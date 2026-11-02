# Run Tapdix locally (demo page)

You need two terminals. Nothing is stored and there is no login: it is a demo of the AI pipeline on **synthetic data**.

**Terminal 1 - API**
```powershell
cd C:\dev\tapdix
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "ml/src"
uvicorn app.main:app --app-dir services/api --port 8000
```
The first start trains the text model and caches it in `ml/models/` (git-ignored): expect 10-60 s, later starts are instant.
Wait for `Application startup complete`.

**Terminal 2 - web page**
```powershell
cd C:\dev\tapdix\apps\web
npm run dev
```
Open <http://localhost:5173>. Interactive API docs: <http://localhost:8000/docs>.

## What to try
| Input | Expected behaviour |
|---|---|
| `Mətbəx kranı su axıdır, təcili lazımdır` | Understood from the text (Santexnika); masters ranked with reasons |
| `paltaryuyan sixmir, cox ses salir` (no diacritics) | Same quality as with diacritics |
| `Нет света в квартире, автомат выбивает` (Russian), urgency Emergency | Electrical; masters who accept emergencies rank higher |
| `Usta lazımdır, şəkildə görünür` + simulated photo "AC unit with a water stain" | Text unclear, **photo used** (HVAC / AC leak) |
| `Kran damır, baxın` + simulated photo "a laptop" | Text and photo conflict: the page asks the customer |
| `Kömək lazımdır` | Not clear enough: asks for more detail and a photo |

Also try: very short text, slang, two problems in one message, and boundary cases such as
`kombi su qızdırıcısı işləmir` (the model splits ~51% plumbing / 40% HVAC and picks plumbing: a known limitation).

## Troubleshooting
* **"Cannot reach the API"** on the page: Terminal 1 is not running or has not finished starting.
* **Port already in use**: close the old terminal, or use another port (and change the proxy in `apps/web/vite.config.ts`).
* **Garbled Azerbaijani letters in the terminal**: run `chcp 65001`.
* The "photo" is a *simulation* (a preset of detector output); there is no image upload until a YOLO model exists.
