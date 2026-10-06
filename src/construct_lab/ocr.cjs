// Runs entirely locally; the first run downloads only English language weights.
const { createWorker, PSM } = require('tesseract.js');
const version = require('tesseract.js/package.json').version;
(async () => {
  const worker = await createWorker('eng', 1, { cachePath: process.argv[3] });
  try {
    await worker.setParameters({ tessedit_pageseg_mode: PSM.AUTO });
    const { data } = await worker.recognize(process.argv[2]);
    process.stdout.write(JSON.stringify({ text: data.text, blocks: [],
      engine: `Tesseract.js ${version} (English, automatic page segmentation)` }));
  } finally { await worker.terminate(); }
})().catch(error => { process.stderr.write(String(error)); process.exit(1); });
