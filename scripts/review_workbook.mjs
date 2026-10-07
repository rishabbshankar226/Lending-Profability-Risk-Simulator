// Authoring QA in ChatGPT Work's primary runtime; not an app dependency.
// Run a copied version from a private OS temp directory with the bundled
// node_modules symlink. Input is the engine's saved workbook specification.
import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const [inputPath, outputDir] = process.argv.slice(2);
if (!inputPath || !outputDir) throw new Error('Provide workbook-spec.json and output directory.');
const spec = JSON.parse(await fs.readFile(inputPath, 'utf8'));
await fs.mkdir(outputDir, {recursive: true});
const workbook = Workbook.create();
for (const sheetSpec of spec.sheets) workbook.worksheets.add(sheetSpec.name);
for (const sheetSpec of spec.sheets) {
  const sheet = workbook.worksheets.getItem(sheetSpec.name);
  sheet.showGridLines = false;
  const cols = Math.max(...sheetSpec.rows.map(r => r.length));
  const rows = sheetSpec.rows.map(r => Array.from({length: cols}, (_, c) => r[c] ?? null));
  sheet.getRangeByIndexes(0,0,rows.length,cols).values = rows;
  const used = sheet.getRangeByIndexes(0,0,rows.length,cols);
  used.format.font = {name:'Arial',size:10,color:'#182c3e'};
  used.format.rowHeight = 20;
  used.format.columnWidth = 25;
  used.format.verticalAlignment = 'center';
  for (const [col, width] of Object.entries(sheetSpec.widths)) {
    sheet.getRangeByIndexes(0,Number(col),rows.length,1).format.columnWidth = width;
  }
  for (const [range, numberFormat] of Object.entries(sheetSpec.formats)) sheet.getRange(range).setNumberFormat(numberFormat);
  for (const cell of sheetSpec.formulas) {
    sheet.getRange(cell.cell).formulas = [[cell.formula]];
    sheet.getRange(cell.cell).setNumberFormat('$#,##0.00;($#,##0.00);"-"');
    sheet.getRange(cell.cell).format.font.color = '#111111';
  }
  if (sheetSpec.name === 'Loan benchmark') sheet.getRange('B6').setNumberFormat('0.0%');
  if (['Monthly snapshot','Cohort snapshot'].includes(sheetSpec.name)) {
    sheet.getRangeByIndexes(1,0,1,cols).format.wrapText = true;
    sheet.getRangeByIndexes(1,0,1,cols).format.rowHeight = 44;
  }
  if (sheetSpec.freeze) sheet.freezePanes.freezeRows(sheetSpec.freeze);
  if (['Summary','Loan benchmark','Default benchmark'].includes(sheetSpec.name)) {
    sheet.getRange('A1').format.font = {name:'Arial',size:14,bold:true,color:'#182c3e'};
  } else {
    sheet.getRangeByIndexes(0,0,1,cols).format = {fill:'#243e54',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:36};
  }
  if (sheetSpec.name.endsWith('benchmark')) {
    sheet.getRangeByIndexes(10,0,1,cols).format = {fill:'#243e54',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:34};
    const editableCells = sheetSpec.name.startsWith('Loan') ? ['B3','B4'] : ['B3','B5','B6'];
    for (const cell of editableCells) sheet.getRange(cell).format = {fill:'#fff4cc',font:{name:'Arial',size:10,color:'#1d4ed8'}};
    // Move long notes out of the small calculator's table.
    const noteRow = sheetSpec.name.startsWith('Loan') ? 8 : 7;
    const note = sheetSpec.rows[noteRow][0];
    sheet.getRangeByIndexes(noteRow,0,1,1).values = [[null]];
    sheet.getRange('H3').values = [[note]];
    sheet.getRange('H3:H4').format.columnWidth = 100;
    sheet.getRange('H4').values = [[sheetSpec.name.startsWith('Loan') ? 'Fixed term: 12 payments. Annual rate 0–100%; principal must be positive.' : 'Default month fixed at 1. Recovery lag 0–3 months.']];
    sheet.getRange('B3').dataValidation = {rule:{type:'decimal',operator:'greaterThan',formula1:0}};
    if (sheetSpec.name.startsWith('Loan')) {
      sheet.getRange('B4').dataValidation = {rule:{type:'decimal',operator:'between',formula1:0,formula2:1}};
      sheet.getRange('B5').dataValidation = {rule:{type:'whole',operator:'equal',formula1:12}};
    } else {
      sheet.getRange('B4').dataValidation = {rule:{type:'whole',operator:'equal',formula1:1}};
      sheet.getRange('B5').dataValidation = {rule:{type:'decimal',operator:'between',formula1:0,formula2:1}};
      sheet.getRange('B6').dataValidation = {rule:{type:'whole',operator:'between',formula1:0,formula2:3}};
    }
  }
}

workbook.recalculate();
const loan = workbook.worksheets.getItem('Loan benchmark');
const defaults = workbook.worksheets.getItem('Default benchmark');
const payment = loan.getRange('B8').values[0][0];
const lastBalance = loan.getRange('F23').values[0][0];
const netLoss = defaults.getRange('B7').values[0][0];
const received = defaults.getRange('E16').values[0][0];
if (Math.abs(payment - 106.61854641401008) > 1e-9 || Math.abs(lastBalance) > .01 || netLoss !== 675 || received !== 225) {
  throw new Error(JSON.stringify({payment,lastBalance,netLoss,received}));
}
// Recalculation checks use edits, rather than trusting cached values.
loan.getRange('B4').values = [[0]];
if (Math.abs(loan.getRange('B8').values[0][0] - 100) > 1e-9) throw new Error('Zero-rate benchmark failed.');
loan.getRange('B4').values = [[.12]];
defaults.getRange('B5').values = [[1]];
if (defaults.getRange('B7').values[0][0] !== 0) throw new Error('Full recovery benchmark failed.');
defaults.getRange('B5').values = [[.25]];
workbook.recalculate();
const errors = await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},maxChars:1800});
console.log(errors.ndjson);
for (const sheetSpec of spec.sheets) {
  const range = sheetSpec.name === 'Loan benchmark' ? 'A1:H26' : sheetSpec.name === 'Default benchmark' ? 'A1:H16' :
                sheetSpec.name === 'Assumptions' ? 'A1:G16' : sheetSpec.name === 'Monthly snapshot' ? 'A1:H10' :
                sheetSpec.name === 'Cohort snapshot' ? 'A1:H10' : undefined;
  const preview = await workbook.render({sheetName:sheetSpec.name,...(range ? {range} : {autoCrop:'all'}),scale:1,format:'png'});
  await fs.writeFile(`${outputDir}/${sheetSpec.name.replaceAll(' ','-')}.png`,new Uint8Array(await preview.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(`${outputDir}/audit-workbook.xlsx`);
await fs.writeFile(`${outputDir}/verification.json`,JSON.stringify({run_id:spec.selected_run_id,payment,lastBalance,netLoss,received,
  recalculation_cases:['zero nominal interest: $100/month','100% recovery: $0 net loss'],engine:'Artifact Tool'},null,2));
console.log(JSON.stringify({run_id:spec.selected_run_id,payment,lastBalance,netLoss,received,outputDir}));
