import { isDesignCanvas } from "./designCanvas";
import { isPptx } from "./slides";

/** A design page: an HTML file whose drawings are inline SVG. A lone .svg is a picture file, not a design. */
export const isDesign = (path: string) => /\.html?$/i.test(path);

/** A file the viewer panel opens instead of the program it belongs to. */
export const isViewable = (path: string) => isPptx(path) || isDesign(path) || isDesignCanvas(path) || isDocMarkdown(path);

/** A Markdown file the Doc editor opens. Whether it is a Doc (its front matter) only the server can say. */
export const isDocMarkdown = (path: string) => /\.md$/i.test(path);
