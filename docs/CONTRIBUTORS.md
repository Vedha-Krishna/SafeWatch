# PettyCrimeSG MVP Progress 🔍
> **For contributors only.** Not linked from the public README.

---

## 🗄 Database & Backend

- [x] Supabase tables created
- [x] `upgrade_migration.sql` written
- [x] FastAPI routes wired up
- [x] Backend connected to `.env`
- [x] `seed_incidents.sql` written
- [ ] Run `seed_incidents.sql` in Supabase
- [ ] Run `upgrade_migration.sql` in Supabase

---

## 🕷 Crawler Agent (Alex)

- [x] Keyword filtering (5 crime types)
- [x] Rejection rules (jokes, vague posts)
- [x] Duplicate detection
- [x] Location extraction (27 SG places)
- [x] Time extraction
- [ ] Real Reddit / social media scraping
- [ ] LLM soft prompt
- [ ] Geocoding (lat/lng always null)
- [ ] Save crawler output to Supabase

---

## 🧹 Cleaner Agent (Alex)

- [x] Whitespace normalization
- [ ] Strip HTML tags & URLs from raw text
- [ ] Remove usernames / handles (`@mentions`)
- [ ] Normalize date & time phrases (`"ytd"` → ISO timestamp)
- [ ] Normalize location text (short forms → full names e.g. `"AMK"` → `"Ang Mo Kio"`)
- [ ] Detect and flag language (English vs non-English)
- [ ] Truncate or summarize excessively long posts
- [ ] Pass cleaned fields into `IncidentState` (`location_text`, `normalized_time` currently not set by cleaner)

---

## 🤖 Classifier Agent (Patrick)

- [x] Category keyword scoring
- [x] LLM authenticity prompt written
- [x] Fix scoring formula (vandalism → 0.72, harassment → 0.71, all known categories now clear the 0.70 threshold)
- [ ] Add `source_reliability` & corroboration scores
- [ ] Set `temperature=0` on LLM calls
- [x] Vector similarity scoring
- [ ] Unreported incident check

---

## ⚖️ Decision Agent (Patrick)

- [x] Write publish / reject / merge to Supabase
- [ ] Merge logic for duplicates
- [ ] Connect decision → map pin

---

## 🔁 Feedback Loops (Patrick)

- [x] `agent_feedback` table in DB
- [x] Feedback API routes
- [x] Classifier → Crawler loop
- [x] Decision → Classifier loop
- [x] Demo one full loop live

---

## 🧠 LangGraph Pipeline (Ameer)

- [x] LangGraph graph built
- [x] Wire pipeline to FastAPI
- [x] Pipeline writes results to Supabase
- [x] API endpoint to trigger pipeline (`POST /api/pipeline/run`)

---

## 🗺 Frontend Map (Vedha)

- [x] Singapore map with pins
- [x] Incident clustering
- [x] Severity colour coding
- [x] Incident detail panel
- [x] Time range + crime type filters
- [x] Sidebar list
- [x] Re-add `fetchIncidents` to `store.ts` — resolved: `loadIncidents` fetches from Supabase and is called on Dashboard mount; falls back to mock data only when DB is empty
- [x] Live updates via Supabase Realtime

---

## 📊 Pitch Deck Slides (Ameer & Vedha)

- [ ] Problem / Challenge slide
- [ ] Solution slide
- [ ] How it works slide (screenshots / video of tech)
- [ ] Ideal Users / Customers slide
- [ ] What makes us unique & value additive slide

---

## 📋 User Survey (Alex & Patrick) — Optional

- [ ] Draft survey questions
- [ ] Collect responses

---

## 🎯 Demo Requirements

- [ ] Full pipeline demo (post → score → decision → pin)
- [ ] Show one agent revision loop
- [ ] 15–30 sample posts ready

---

## ✅ Devpost Submission Checklist

- [ ] Invite teammates to join the Devpost submission
- [ ] Add project title + elevator pitch
- [ ] Write your project story (Devpost template)
- [ ] Upload screenshots
- [ ] Upload demo video (upload to YouTube first, then paste the public link)
- [ ] Upload pitch deck PDF under "Upload a File"
- [ ] Select the theme you're competing in
- [ ] Add GitHub repository link (with setup steps in README)
- [ ] Review reminders and agree to T&Cs, then submit
