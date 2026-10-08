const t = require("../static/js/chord_tools.js");
const cases = [["Cmaj7","C"],["Am7","Am"],["Dsus4","D"],["Cadd9","C"],["G/B","G/B"],["F#m7/C#","F#m/C#"],["C7","C"],["Asus2","A"],["Bbmaj7","Bb"],["C#m7b5","C#m"],["Em9","Em"],["Cdim7","Cdim"],["Caug7","Caug"],["Cmin7","Cm"],["Am","Am"],["C7#9","C"]];
for (const pair of cases) {
  if (t.simplifyChord(pair[0]) !== pair[1]) {
    console.error(pair[0], t.simplifyChord(pair[0]));
    process.exit(1);
  }
}
const ideas = t.suggestCapos(["B","F#","C#m"]);
if (ideas[0].fret !== 4 || ideas[0].chords.join(",") !== "G,D,Am") process.exit(1);
if (t.transformText("[B]line [F#m7]here", {steps: -4, simplify: true}) !== "[G]line [Dm]here") process.exit(1);
console.log("ok");
