import { isDocx } from "./docxReview";
import { isPptx } from "./slides";

/** A design page: an HTML file whose drawings are inline SVG. A lone .svg is a picture file, not a design. */
export const isDesign = (path: string) => /\.html?$/i.test(path);

/** A file the viewer panel opens instead of the program it belongs to. */
export const isViewable = (path: string) => isDocx(path) || isPptx(path) || isDesign(path);
