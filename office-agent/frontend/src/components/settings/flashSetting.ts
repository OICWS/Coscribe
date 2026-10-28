const FLASH_MS = 2700;
const FLASH_REDUCED_MS = 2200;

const reducedMotion = () => document.documentElement.dataset.motion === "reduced";

/** A wobbly line, drawn like a pen would: a sine wave whose height and pitch drift a little. */
function wavyPath(width: number): string {
  const points: string[] = [];
  const step = 4;
  for (let x = 0; x <= width; x += step) {
    const y = 4 + Math.sin(x / 3.2) * (1.6 + 0.5 * Math.sin(x / 17)) + Math.sin(x / 9) * 0.4;
    points.push(`${x === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(2)}`);
  }
  return points.join(" ");
}

/** Scrolls a settings row into view, then draws a wavy underline under its name and lights the
 * row up before fading it back. Returns false when the row isn't on the page. */
export function flashSetting(label: string, root: ParentNode = document): Promise<boolean> {
  const row = Array.from(root.querySelectorAll<HTMLElement>("[data-setting-label]")).find(
    (el) => el.dataset.settingLabel === label,
  );
  if (!row) return Promise.resolve(false);
  const reduced = reducedMotion();
  row.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "center" });

  return new Promise((resolve) => {
    // Starts once the scroll has stopped moving, so the underline isn't drawn on a row still in flight.
    let last = row.getBoundingClientRect().top;
    let still = 0;
    const settle = () => {
      const top = row.getBoundingClientRect().top;
      still = Math.abs(top - last) < 0.5 ? still + 1 : 0;
      last = top;
      if (still >= 4 || reduced) start();
      else requestAnimationFrame(settle);
    };
    const start = () => {
      const name = row.querySelector<HTMLElement>("[data-setting-name]");
      let svg: SVGSVGElement | null = null;
      if (name) {
        const range = document.createRange();
        range.selectNodeContents(name);
        const width = Math.ceil(range.getBoundingClientRect().width);
        svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("class", "setting-underline");
        svg.setAttribute("width", String(width));
        svg.setAttribute("height", "8");
        svg.setAttribute("aria-hidden", "true");
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", wavyPath(width));
        path.setAttribute("pathLength", "1");
        svg.appendChild(path);
        name.appendChild(svg);
      }
      row.classList.remove("setting-flash");
      void row.offsetWidth;
      row.classList.add("setting-flash");
      window.setTimeout(() => {
        row.classList.remove("setting-flash");
        svg?.remove();
        resolve(true);
      }, reduced ? FLASH_REDUCED_MS : FLASH_MS);
    };
    requestAnimationFrame(settle);
  });
}
