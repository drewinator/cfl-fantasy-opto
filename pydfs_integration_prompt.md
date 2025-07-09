
# Claude Code Prompt – Add PyDFS Engine to CFL Fantasy Optimizer

1. Create a custom “CFL Fantasy” sport/site inside **pydfs‑lineup‑optimizer**.
2. Implement a `CFLPydfsOptimizer` wrapper with proper roster rules and captain logic.
3. Update `api_server.py` so you can choose between the existing PuLP solver and the new PyDFS solver via `engine` query param.
4. Adjust `requirements.txt`.

---

```plaintext
# === CONTEXT ==========================================================
You’re working inside the repo Andrew showed you:
cfl-fantasy-opto/
├── manifest.json
├── popup.html/js
├── content.js
├── optimizerBridge.js
└── optimizer/
    ├── api_server.py
    ├── custom_cfl_optimizer.py     # ← existing PuLP solver (still keep)
    ├── cfl_optimizer.py            # ← stub we wrote earlier (replace)
    └── requirements.txt

Right now the Flask API (api_server.py) imports CustomCFLOptimizer.
We want a **second engine** based on pydfs-lineup-optimizer that fully
supports the CFL Fantasy roster rules & MVP (2×) captain.

Official docs: https://pydfs-lineup-optimizer.readthedocs.io/en/latest/
Key tips from docs:

• You can register a **custom Site** and **Sport** by subclassing or by
  using `Site.register_site('MY_SITE')`, `Sport.register_sport('MY_SPORT')`.
• You create `LineupPosition` objects to define roster structure.
• You can subclass `LineupOptimizer` and override `settings_class`
  or `optimizer_settings` to tweak constraints.
• A captain/MVP slot can be modeled either (a) by creating an extra
  `LineupPosition('CPT', ('QB','RB','WR'), salary_weight=1.5,
  max_from_team=1, point_multiplier=2)` OR (b) by brute-forcing
  candidates (simpler for this sprint).

For MVP we’ll **reuse the brute-force loop** you already wrote in
custom_cfl_optimizer.py to avoid deep pydfs surgery.

CFL fantasy roster rules (as confirmed in custom solver):
• 7 total players:
    1 QB
    2 RB
    2 WR
    1 FLEX (RB or WR)
    1 DEF
• Salary cap = 70 000
• Max 3 players per real-life team
• One of the non-DEF players is designated MVP/Captain and scores 2× pts
  (no salary change).  We’ll brute-force this.

-----------------------------------------------------------------------
# === TASKS FOR CLAUDE CODE ===========================================

1. **Create a new file:**  `optimizer/cfl_pydfs_optimizer.py`

   ```python
   """
   CFL Fantasy optimizer built on pydfs-lineup-optimizer
   """
   from pydfs_lineup_optimizer import (
       Site, Sport, Player, LineupOptimizer,
       Lineup, LineupPosition
   )
   import itertools

   # Register custom site/sport
   Site.register_site('CFLFANTASY')
   Sport.register_sport('CFL')

   # ---- Player wrapper ----
   class CFLPlayer(Player):
       pass  # inherited fields are fine

   # ---- Optimizer ----
   class CFLPydfsOptimizer:
       SALARY_CAP = 70000
       ROSTER_POSITIONS = [
           LineupPosition('QB'),
           LineupPosition('RB'),
           LineupPosition('RB'),
           LineupPosition('WR'),
           LineupPosition('WR'),
           LineupPosition('FLEX', ('RB', 'WR')),
           LineupPosition('DEF'),
       ]

       def __init__(self):
           self.optimizer = LineupOptimizer(
               site=Site('CFLFANTASY'),
               sport=Sport('CFL'),
           )
           self.optimizer.set_lineup_positions(self.ROSTER_POSITIONS)
           self.optimizer.settings.__dict__.update({
               'budget': self.SALARY_CAP,
               'max_from_team': 3,
           })

       # ------------- Data Loading ------------------
       def load_players_from_json(self, players_json):
           self.optimizer.players = []  # reset
           for p in players_json:
               player = CFLPlayer(
                   player_id=p['id'],
                   first_name=p['first_name'],
                   last_name=p['last_name'],
                   positions=[p['position']],
                   team=p['team'],
                   salary=int(p['salary']),
                   fppg=float(p['projectedPoints']),
               )
               self.optimizer.add_player(player)

       # ------------- MVP brute-force ----------------
       def get_best_lineup(self):
           best_lineup = None
           best_points = -1

           candidates = [p for p in self.optimizer.players if 'DEF' not in p.positions]

           for captain in candidates:
               captain.fppg *= 2  # add MVP multiplier
               try:
                   lineup = self.optimizer.optimize(10_000)
               except Exception:
                   captain.fppg /= 2
                   continue
               points = lineup.fantasy_points
               if points > best_points:
                   best_points = points
                   best_lineup = lineup.copy(lineup.players)
               captain.fppg /= 2  # reset

           return best_lineup

       # API helper
       def optimize_from_request(self, data):
           self.load_players_from_json(data['players'])
           lineup = self.get_best_lineup()
           if not lineup:
               raise ValueError("No valid lineup found")
           return [{
               'id': p.id,
               'name': f'{p.first_name} {p.last_name}',
               'team': p.team,
               'position': p.positions[0],
               'salary': p.salary,
               'projection': round(p.fppg, 2),
           } for p in lineup.players]
   ```

2. **Remove** the old stub `optimizer/cfl_optimizer.py`
   or replace its contents with:

   ```python
   from optimizer.cfl_pydfs_optimizer import CFLPydfsOptimizer
   ```

3. **Modify** `optimizer/api_server.py`

   ```python
   from flask import Flask, request, jsonify
   from custom_cfl_optimizer import CustomCFLOptimizer
   from cfl_pydfs_optimizer import CFLPydfsOptimizer

   app = Flask(__name__)

   @app.route('/optimize', methods=['POST'])
   def optimize():
       data = request.get_json()
       engine = request.args.get('engine', 'pulp')

       optimizer = CFLPydfsOptimizer() if engine == 'pydfs' else CustomCFLOptimizer()

       try:
           lineup = optimizer.optimize_from_request(data)
           return jsonify({'success': True, 'lineup': lineup})
       except Exception as e:
           return jsonify({'success': False, 'error': str(e)}), 400
   ```

4. **Update** `optimizer/requirements.txt`:

   ```
   flask
   pulp
   pydfs-lineup-optimizer
   ```

5. **(Optional UI)**  
   Add a dropdown in `popup.html` so the user can pick
   “PuLP” or “PyDFS” before clicking **Optimize**.

# === END PROMPT =======================================================
```

```

# How to use

1. Open Claude Code.  
2. Paste the **whole block** (everything between the triple backticks) into the Claude Code prompt.  
3. Let Claude generate new files / edits.  
4. `pip install -r optimizer/requirements.txt`  
5. Run `python optimizer/api_server.py` and test:
   - `POST /optimize` → uses PuLP (default)  
   - `POST /optimize?engine=pydfs` → uses new PyDFS solver.

Enjoy swapping solvers and comparing results! 🏈
