import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const filePath = path.join(__dirname, '..', 'src', 'components', 'DigitalHumanForm.vue');
let content = fs.readFileSync(filePath, 'utf-8');

// Remove onSubtitleEnabledChange function and its comment
const find = "// \u5B57\u5E55\u529F\u80FD\uFF1A\u76F4\u63A5\u5141\u8BB8\uFF08\u5DF2\u53D6\u6D88VIP\u9650\u5236\uFF09\nfunction onSubtitleEnabledChange(val: boolean) {\n  // \u6240\u6709\u4EBA\u90FD\u53EF\u4EE5\u4F7F\u7528\u5B57\u5E55\u529F\u80FD\n}";
const idx = content.indexOf(find);
if (idx >= 0) {
  // Remove from beginning of this comment to after the closing brace
  const before = content.lastIndexOf("\n", idx - 1);
  const after = content.indexOf("\n", idx + find.length);
  if (after > 0) {
    content = content.substring(0, before) + "\n" + content.substring(after + 1);
    console.log("Removed onSubtitleEnabledChange");
  }
} else {
  console.log("Pattern not found");
  // Try more direct search
  const f2 = "onSubtitleEnabledChange";
  const idx2 = content.indexOf(f2);
  if (idx2 > 0) {
    console.log("Found at", idx2);
    console.log(content.substring(idx2 - 100, idx2 + 120));
  }
}

fs.writeFileSync(filePath, content, 'utf-8');
console.log("Done");
