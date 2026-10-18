/** The ten layouts of the New slide dialog (design §7), as sections in the current slide's own
 * colours and font, so a new slide matches the deck coscribe made. Each heading is the slide's
 * title (`id="title"`), which the deck's outline reads. */

export interface SlideLook {
  background: string;
  text: string;
  muted: string;
  accent: string;
  font: string;
}

export interface SlideLayout {
  name: string;
  source: string;
}

const box = (x: number, y: number, w: number, h: number) => `left:${x}px;top:${y}px;width:${w}px;height:${h}px`;
const escape = (text: string) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

export function slideLayouts(look: SlideLook): SlideLayout[] {
  const section = (body: string) =>
    `<section style="background:${look.background};color:${look.text};font-family:${escape(look.font)}">${body}</section>`;
  const heading = (text: string) => `<h2 id="title" style="${box(160, 110, 1600, 80)}">${text}</h2>`;
  const body = (text: string, x = 160, y = 240, w = 1600, h = 120) => `<p style="${box(x, y, w, h)};color:${look.muted}">${text}</p>`;
  return [
    { name: "Blank", source: section("") },
    {
      name: "Title",
      source: section(
        `<h1 id="title" style="${box(160, 400, 1600, 110)};font-size:80px">Presentation title</h1>` +
          body("A one-line subtitle for the presentation.", 160, 530, 1600, 60),
      ),
    },
    {
      name: "Section",
      source: section(
        `<p style="${box(160, 420, 800, 40)};font-size:24px;letter-spacing:3px;color:${look.accent};font-weight:700">SECTION 01</p>` +
          `<h1 id="title" style="${box(160, 470, 1600, 110)};font-size:72px">Section title</h1>`,
      ),
    },
    { name: "Title + body", source: section(heading("Heading") + body("Body copy goes here. Double-click any text to edit it in place.")) },
    {
      name: "Bullets",
      source: section(
        heading("Key points") +
          `<ul style="${box(160, 250, 1600, 400)};color:${look.muted}"><li>First point</li><li>Second point</li><li>Third point</li></ul>`,
      ),
    },
    {
      name: "Two columns",
      source: section(
        heading("Compare") +
          `<h3 style="${box(160, 260, 760, 50)}">Left</h3>` +
          body("Left column copy.", 160, 330, 760, 200) +
          `<h3 style="${box(1000, 260, 760, 50)}">Right</h3>` +
          body("Right column copy.", 1000, 330, 760, 200),
      ),
    },
    { name: "Table", source: section(heading("Summary") + table(look)) },
    {
      name: "Quote",
      source: section(
        `<h2 id="title" style="${box(260, 380, 1400, 200)};font-size:56px;text-align:center">“A memorable line worth a whole slide.”</h2>` +
          `<p style="${box(260, 620, 1400, 50)};font-size:24px;text-align:center;color:${look.muted}">— Attribution</p>`,
      ),
    },
    {
      name: "Image + caption",
      source: section(
        `<x-shape data-shape="rect" style="${box(560, 150, 800, 560)};background:#E5E7EB"/>` +
          `<p id="title" style="${box(560, 740, 800, 50)};font-size:24px;text-align:center;color:${look.muted}">Caption for the image.</p>`,
      ),
    },
    { name: "Closing", source: section(`<h1 id="title" style="${box(160, 460, 1600, 110)};font-size:80px">Thank you</h1>`) },
  ];
}

function table(look: SlideLook): string {
  const header = ["Item", "Status", "Owner"].map((text) => `<th style="background:${look.accent};color:#FFFFFF">${text}</th>`).join("");
  const row = "<tr><td></td><td></td><td></td></tr>";
  return `<table style="${box(160, 250, 1600, 240)};font-size:28px;border-color:#CBD2DC"><tr>${header}</tr>${row}${row}</table>`;
}
