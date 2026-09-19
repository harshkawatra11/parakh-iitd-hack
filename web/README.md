# Parakh — web console

Next.js 15 (App Router) review console for the Corporate Heist shortlist.

```
npm install
npm run dev      # http://localhost:3000
npm run build
```

Data lives in `src/data/*.json`, generated from the Python pipeline's export by
`../scripts/prep_web_data.py`. To refresh after re-running `main.py` with
`PARAKH_EXPORT=1`:

```
python ../scripts/prep_web_data.py
cp public/data/*.json src/data/
```

Stack: Next.js 15, TypeScript, Tailwind CSS v4, Framer Motion, GSAP, Chart.js
(via react-chartjs-2). Archival paper-and-ink design system — no gradients, no
glassmorphism, tabular-numeral mono for every ID and number.
