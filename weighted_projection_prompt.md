
# Codex Prompt – Add Weighted-Average Projections (v0.1)

**Repository:** `drewinator/cfl-fantasy-opto`  
**Objective:** Introduce a simple **weighted‑average projection** model and connect it end‑to‑end (API → content script → UI toggle).

---

## Tasks

### 1 · Create `optimizer/projections.py`

```python
"""Weighted‑average projections for CFL fantasy.

Formula:
    proj = (0.5 * last_game_pts) +            (0.3 * average of previous 2 games) +            (0.2 * season_avgPts)

If the player has < 2 games, fall back to site `projectedScores`.
Round to two decimals.

Public function
    build_projection_map(players_json) -> dict[int, float]
"""
```

* Parse each player’s `stats.points.gws` (dict of week → points).  
* Use pure Python or pandas (already in requirements).  
* Return `{player_id: projection}`.

---

### 2 · Edit `optimizer/api_server.py`

* **Add** route **`/projections`** (`GET`) that returns the projection map.  
* Modify **`/optimize`**:  
  * Accept query param **`source`** (`our` or `site`, default =`our`).  
  * When `source=="our"`, call `build_projection_map()` and overwrite  
    `player["stats"]["projectedScores"]` before passing players to the optimizer.

---

### 3 · Update `content.js`

* After building `playerData`, fetch `/projections` (cache with  
  `chrome.storage.local` for 60 min).  
* Merge into each player object:

```js
player.projectedPoints = projMap[player.id];
```

  unless the user has selected **Site** projections.

---

### 4 · UI toggle in the injected lineup panel

```html
<label>Proj:</label>
<select id="projSource">
  <option value="our">Our</option>
  <option value="site">Site</option>
</select>
```

On change, re‑render projection numbers and total points **without** re‑calling the optimizer.

---

### 5 · Unit test

Create **`tests/test_projections.py`**

```python
import json, optimizer.projections as p

sample = json.load(open("json_files/players_sample.json"))
mp = p.build_projection_map(sample)

assert isinstance(mp, dict)
assert len(mp) == len(sample)
```

*(Add a tiny fixture `players_sample.json` if one doesn’t exist: three players × three game‑weeks.)*

---

### 6 · Documentation

Append to **README**:

> **Custom projections (v0.1)** — weighted‑average formula and how to switch via the “Proj: Our / Site” toggle in the UI.

---

### 7 · Compatibility

Calling `/optimize?source=site` must keep the original behaviour (use site projections).

---

#### Commit message suggestion

```text
feat(projections): add weighted‑average model and API/UI integration
```

---

*End prompt*
