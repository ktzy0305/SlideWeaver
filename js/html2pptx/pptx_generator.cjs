const { normalizeLocalPath, isReadableFile, EMU_PER_IN } = require('./utils.cjs');
const sharp = require('sharp');

async function getImageDimensionsPx(imagePath) {
    try {
        const metadata = await sharp(imagePath).metadata();
        const width = Number(metadata.width);
        const height = Number(metadata.height);
        if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return null;
        return { width, height };
    } catch {
        return null;
    }
}

function aspectFitIntoFrame({ frameX, frameY, frameW, frameH }, { imgW, imgH }) {
    if (frameW <= 0 || frameH <= 0 || imgW <= 0 || imgH <= 0) {
        return { x: frameX, y: frameY, w: frameW, h: frameH };
    }

    const imgAspect = imgW / imgH;
    const frameAspect = frameW / frameH;

    let w;
    let h;
    if (imgAspect >= frameAspect) {
        // Image is wider than frame: fit to width.
        w = frameW;
        h = frameW / imgAspect;
    } else {
        // Image is taller than frame: fit to height.
        h = frameH;
        w = frameH * imgAspect;
    }

    const x = frameX + (frameW - w) / 2;
    const y = frameY + (frameH - h) / 2;
    return { x, y, w, h };
}

function parseObjectPosition(objectPosition) {
    // Browser default is typically "50% 50%".
    // We support the common keywords produced by CSS (e.g. "center top").
    const raw = (objectPosition || '').toString().trim().toLowerCase();
    if (!raw) return { xAlign: 'center', yAlign: 'center' };

    const parts = raw.split(/\s+/).filter(Boolean);
    const first = parts[0] || 'center';
    const second = parts[1] || 'center';

    const toAlign = (token, axis) => {
        if (token === 'left') return 'left';
        if (token === 'right') return 'right';
        if (token === 'top') return 'top';
        if (token === 'bottom') return 'bottom';
        if (token === 'center') return 'center';

        // Percentages (e.g. 0%, 50%, 100%)
        const m = token.match(/^(-?\d+(?:\.\d+)?)%$/);
        if (m) {
            const v = parseFloat(m[1]);
            if (!Number.isFinite(v)) return 'center';
            if (v <= 10) return axis === 'x' ? 'left' : 'top';
            if (v >= 90) return axis === 'x' ? 'right' : 'bottom';
            return 'center';
        }

        return 'center';
    };

    // If only one token is present, CSS treats it as x and uses center for y.
    const xToken = first;
    const yToken = parts.length > 1 ? second : 'center';

    return {
        xAlign: toAlign(xToken, 'x'),
        yAlign: toAlign(yToken, 'y'),
    };
}

function aspectFitIntoFrameAligned({ frameX, frameY, frameW, frameH }, { imgW, imgH }, { xAlign, yAlign }) {
    const fitted = aspectFitIntoFrame({ frameX, frameY, frameW, frameH }, { imgW, imgH });

    // aspectFitIntoFrame returns centered positioning. Adjust based on desired alignment.
    let x = fitted.x;
    let y = fitted.y;

    if (xAlign === 'left') x = frameX;
    else if (xAlign === 'right') x = frameX + (frameW - fitted.w);

    if (yAlign === 'top') y = frameY;
    else if (yAlign === 'bottom') y = frameY + (frameH - fitted.h);

    return { x, y, w: fitted.w, h: fitted.h };
}

/**
 * Add background to slide
 */
async function addBackground(slideData, targetSlide) {
    if (slideData.background.type === 'image' && slideData.background.path) {
        const imagePath = normalizeLocalPath(slideData.background.path);
        if (isReadableFile(imagePath)) {
            targetSlide.background = { path: imagePath };
        }
    } else if (slideData.background.type === 'color' && slideData.background.value) {
        targetSlide.background = { color: slideData.background.value };
    }
}

/**
 * Add elements to slide
 */
async function addElements(slideData, targetSlide, presentation) {
    const slideWidthIn = presentation && presentation.presLayout && presentation.presLayout.width
        ? presentation.presLayout.width / EMU_PER_IN
        : null;

    const slideHeightIn = presentation && presentation.presLayout && presentation.presLayout.height
        ? presentation.presLayout.height / EMU_PER_IN
        : null;

    for (const element of slideData.elements) {
        if (element.type === 'image') {
            const imagePath = normalizeLocalPath(element.src);
            if (!isReadableFile(imagePath)) continue;

            const dims = await getImageDimensionsPx(imagePath);

            let { x, y, w, h } = element.position;
            if (dims) {
                const align = parseObjectPosition(element.style && element.style.objectPosition);
                const fitted = aspectFitIntoFrameAligned(
                    { frameX: x, frameY: y, frameW: w, frameH: h },
                    { imgW: dims.width, imgH: dims.height },
                    align
                );
                x = fitted.x;
                y = fitted.y;
                w = fitted.w;
                h = fitted.h;
            }

            // Clamp to slide bounds as a last resort.
            if (slideWidthIn != null) {
                x = Math.max(0, x);
                w = Math.max(0, Math.min(w, slideWidthIn - x));
            }
            if (slideHeightIn != null) {
                y = Math.max(0, y);
                h = Math.max(0, Math.min(h, slideHeightIn - y));
            }

            targetSlide.addImage({ path: imagePath, x, y, w, h });
        } else if (element.type === 'line') {
            targetSlide.addShape(presentation.ShapeType.line, {
                x: element.x1,
                y: element.y1,
                w: element.x2 - element.x1,
                h: element.y2 - element.y1,
                line: { color: element.color, width: element.width }
            });
        } else if (element.type === 'shape') {
            const shapeOptions = {
                x: element.position.x,
                y: element.position.y,
                w: element.position.w,
                h: element.position.h,
                shape: element.shape.rectRadius > 0 ? presentation.ShapeType.roundRect : presentation.ShapeType.rect
            };

            if (element.shape.fill) {
                shapeOptions.fill = { color: element.shape.fill };
                if (element.shape.transparency != null) shapeOptions.fill.transparency = element.shape.transparency;
            }
            if (element.shape.line) shapeOptions.line = element.shape.line;
            if (element.shape.rectRadius > 0) shapeOptions.rectRadius = element.shape.rectRadius;
            if (element.shape.shadow) shapeOptions.shadow = element.shape.shadow;

            targetSlide.addText(element.text || '', shapeOptions);
        } else if (element.type === 'list') {
            const listOptions = {
                x: element.position.x,
                y: element.position.y,
                w: element.position.w,
                h: element.position.h,
                fontSize: element.style.fontSize,
                fontFace: element.style.fontFace,
                color: element.style.color,
                align: element.style.align,
                valign: 'top',
                lineSpacing: element.style.lineSpacing,
                paraSpaceBefore: element.style.paraSpaceBefore,
                paraSpaceAfter: element.style.paraSpaceAfter,
                margin: element.style.margin
            };
            if (element.style.margin) listOptions.margin = element.style.margin;
            targetSlide.addText(element.items, listOptions);
        } else if (element.type === 'table') {
            // Convert extracted table data to PptxGenJS format
            const pptxRows = [];

            for (const row of element.rows) {
                const pptxRow = [];

                for (const cell of row) {
                    // Build cell object for PptxGenJS
                    const pptxCell = {
                        text: cell.text,
                        options: {}
                    };

                    // Map cell options to PptxGenJS format
                    const opts = cell.options;
                    if (opts.bold) pptxCell.options.bold = true;
                    if (opts.italic) pptxCell.options.italic = true;
                    if (opts.underline) pptxCell.options.underline = true;
                    if (opts.fontSize) pptxCell.options.fontSize = opts.fontSize;
                    if (opts.fontFace) pptxCell.options.fontFace = opts.fontFace;
                    if (opts.color) pptxCell.options.color = opts.color;
                    if (opts.fill) pptxCell.options.fill = opts.fill;
                    if (opts.align) pptxCell.options.align = opts.align;
                    if (opts.valign) pptxCell.options.valign = opts.valign;
                    if (opts.margin !== undefined) pptxCell.options.margin = opts.margin;
                    if (opts.border) pptxCell.options.border = opts.border;
                    if (opts.colspan) pptxCell.options.colspan = opts.colspan;
                    if (opts.rowspan) pptxCell.options.rowspan = opts.rowspan;

                    pptxRow.push(pptxCell);
                }

                pptxRows.push(pptxRow);
            }

            // Build table-level options
            const tableOptions = {
                x: element.position.x,
                y: element.position.y,
                w: element.position.w,
                h: element.position.h
            };

            // Add table to slide
            targetSlide.addTable(pptxRows, tableOptions);
        } else {
            // Check if text is single-line (height suggests one line)
            const lineHeight = element.style.lineSpacing || element.style.fontSize * 1.2;
            const isSingleLine = element.position.h <= lineHeight * 1.5;

            const hasHyperlink = Array.isArray(element.text) && element.text.some(
                (run) => run && run.options && run.options.hyperlink && run.options.hyperlink.url
            );

            let adjustedX = element.position.x;
            let adjustedW = element.position.w;

            // Make single-line text 2% wider to account for underestimate
            // For hyperlinks, widen more because PowerPoint font metrics often differ from Chromium.
            if (isSingleLine || hasHyperlink) {
                const widthIncrease = hasHyperlink
                    ? Math.max(element.position.w * 0.08, 0.25)
                    : (element.position.w * 0.02);
                const align = element.style.align;

                if (align === 'center') {
                    // Center: expand both sides
                    adjustedX = element.position.x - (widthIncrease / 2);
                    adjustedW = element.position.w + widthIncrease;
                } else if (align === 'right') {
                    // Right: expand to the left
                    adjustedX = element.position.x - widthIncrease;
                    adjustedW = element.position.w + widthIncrease;
                } else {
                    // Left (default): expand to the right
                    adjustedW = element.position.w + widthIncrease;
                }
            }

            // Clamp to slide width to avoid accidental overflow.
            if (slideWidthIn != null) {
                const maxW = Math.max(0, slideWidthIn - adjustedX);
                adjustedW = Math.min(adjustedW, maxW);
            }

            const textOptions = {
                x: adjustedX,
                y: element.position.y,
                w: adjustedW,
                h: element.position.h,
                fontSize: element.style.fontSize,
                fontFace: element.style.fontFace,
                color: element.style.color,
                bold: element.style.bold,
                italic: element.style.italic,
                underline: element.style.underline,
                valign: 'top',
                lineSpacing: element.style.lineSpacing,
                paraSpaceBefore: element.style.paraSpaceBefore,
                paraSpaceAfter: element.style.paraSpaceAfter,
                inset: 0  // Remove default PowerPoint internal padding
            };

            if (element.style.align) textOptions.align = element.style.align;
            if (element.style.margin) textOptions.margin = element.style.margin;
            if (element.style.rotate !== undefined) textOptions.rotate = element.style.rotate;
            if (element.style.transparency !== null && element.style.transparency !== undefined) textOptions.transparency = element.style.transparency;

            targetSlide.addText(element.text, textOptions);
        }
    }
}

module.exports = {
    addBackground,
    addElements
};
