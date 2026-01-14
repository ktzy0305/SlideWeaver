/**
 * DOM Scanner Module
 * 
 * This module contains functions that are executed within the context of the browser (via Playwright)
 * to scan the DOM and extract information needed for PPTX generation.
 * 
 * It includes:
 * - getBodyDimensions: Measures the body size to check for content overflow.
 * - extractSlideData: Serializes the DOM structure into a JSON-compatible format that describes
 *   slide elements (text, images, shapes, lists, etc.), styles (colors, fonts, positioning),
 *   and background information.
 * 
 * Note: The functions inside `getSlideDataFromDom` are serialized and sent to the browser,
 * so they must be self-contained and cannot reference external variables from the Node.js scope
 * (except for constants defined inside the function itself).
 */
const { PT_PER_PX } = require('./utils.cjs');

// Logic to run inside the browser to get dimensions
async function getBodyDimensions(page) {
    const bodyDimensions = await page.evaluate(() => {
        const body = document.body;
        const style = window.getComputedStyle(body);

        return {
            width: parseFloat(style.width),
            height: parseFloat(style.height),
            scrollWidth: body.scrollWidth,
            scrollHeight: body.scrollHeight
        };
    });

    const errors = [];
    const widthOverflowPx = Math.max(0, bodyDimensions.scrollWidth - bodyDimensions.width - 1);
    const heightOverflowPx = Math.max(0, bodyDimensions.scrollHeight - bodyDimensions.height - 1);

    const widthOverflowPt = widthOverflowPx * PT_PER_PX;
    const heightOverflowPt = heightOverflowPx * PT_PER_PX;

    if (widthOverflowPt > 0 || heightOverflowPt > 0) {
        const directions = [];
        if (widthOverflowPt > 0) directions.push(`${widthOverflowPt.toFixed(1)}pt horizontally`);
        if (heightOverflowPt > 0) directions.push(`${heightOverflowPt.toFixed(1)}pt vertically`);
        const reminder = heightOverflowPt > 0 ? ' (Remember: leave 0.5" margin at bottom of slide)' : '';
        errors.push(`HTML content overflows body by ${directions.join(' and ')}${reminder}`);
    }

    return { ...bodyDimensions, errors };
}

// Logic to run inside the browser to extract all slide data
// This function must be self-contained as it is serialized to the browser
const getSlideDataFromDom = () => {
    const PT_PER_PX = 0.75;
    const PX_PER_IN = 96;

    // Fonts that are single-weight and should not have bold applied
    const SINGLE_WEIGHT_FONTS = ['impact'];

    // Helper: Check if a font should skip bold formatting
    const shouldSkipBold = (fontFamily) => {
        if (!fontFamily) return false;
        const normalizedFont = fontFamily.toLowerCase().replace(/['"]/g, '').split(',')[0].trim();
        return SINGLE_WEIGHT_FONTS.includes(normalizedFont);
    };

    // Unit conversion helpers
    const pxToInch = (px) => px / PX_PER_IN;
    const pxToPoints = (pxStr) => parseFloat(pxStr) * PT_PER_PX;
    const rgbToHex = (rgbStr) => {
        // Handle transparent backgrounds by defaulting to white
        if (rgbStr === 'rgba(0, 0, 0, 0)' || rgbStr === 'transparent') return 'FFFFFF';

        const match = rgbStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (!match) return 'FFFFFF';
        return match.slice(1).map(n => parseInt(n).toString(16).padStart(2, '0')).join('');
    };

    const extractAlpha = (rgbStr) => {
        const match = rgbStr.match(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)/);
        if (!match || !match[4]) return null;
        const alpha = parseFloat(match[4]);
        return Math.round((1 - alpha) * 100);
    };

    const applyTextTransform = (text, textTransform) => {
        if (textTransform === 'uppercase') return text.toUpperCase();
        if (textTransform === 'lowercase') return text.toLowerCase();
        if (textTransform === 'capitalize') {
            return text.replace(/\b\w/g, c => c.toUpperCase());
        }
        return text;
    };

    // Extract rotation angle from CSS transform and writing-mode
    const getRotation = (transform, writingMode) => {
        let angle = 0;

        // Handle writing-mode first
        if (writingMode === 'vertical-rl') {
            angle = 90;
        } else if (writingMode === 'vertical-lr') {
            angle = 270;
        }

        // Then add any transform rotation
        if (transform && transform !== 'none') {
            const rotateMatch = transform.match(/rotate\((-?\d+(?:\.\d+)?)deg\)/);
            if (rotateMatch) {
                angle += parseFloat(rotateMatch[1]);
            } else {
                const matrixMatch = transform.match(/matrix\(([^)]+)\)/);
                if (matrixMatch) {
                    const values = matrixMatch[1].split(',').map(parseFloat);
                    const matrixAngle = Math.atan2(values[1], values[0]) * (180 / Math.PI);
                    angle += Math.round(matrixAngle);
                }
            }
        }

        angle = angle % 360;
        if (angle < 0) angle += 360;

        return angle === 0 ? null : angle;
    };

    // Get position/dimensions accounting for rotation
    const getPositionAndSize = (element, rect, rotation) => {
        if (rotation === null) {
            return { x: rect.left, y: rect.top, w: rect.width, h: rect.height };
        }

        const isVertical = rotation === 90 || rotation === 270;

        if (isVertical) {
            const centerX = rect.left + rect.width / 2;
            const centerY = rect.top + rect.height / 2;

            return {
                x: centerX - rect.height / 2,
                y: centerY - rect.width / 2,
                w: rect.height,
                h: rect.width
            };
        }

        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        return {
            x: centerX - element.offsetWidth / 2,
            y: centerY - element.offsetHeight / 2,
            w: element.offsetWidth,
            h: element.offsetHeight
        };
    };

    // Parse CSS box-shadow into PptxGenJS shadow properties
    const parseBoxShadow = (boxShadow) => {
        if (!boxShadow || boxShadow === 'none') return null;

        const insetMatch = boxShadow.match(/inset/);
        if (insetMatch) return null;

        const colorMatch = boxShadow.match(/rgba?\([^)]+\)/);
        const parts = boxShadow.match(/([-\d.]+)(px|pt)/g);

        if (!parts || parts.length < 2) return null;

        const offsetX = parseFloat(parts[0]);
        const offsetY = parseFloat(parts[1]);
        const blur = parts.length > 2 ? parseFloat(parts[2]) : 0;

        let angle = 0;
        if (offsetX !== 0 || offsetY !== 0) {
            angle = Math.atan2(offsetY, offsetX) * (180 / Math.PI);
            if (angle < 0) angle += 360;
        }

        const offset = Math.sqrt(offsetX * offsetX + offsetY * offsetY) * PT_PER_PX;

        let opacity = 0.5;
        if (colorMatch) {
            const opacityMatch = colorMatch[0].match(/[\d.]+\)$/);
            if (opacityMatch) {
                opacity = parseFloat(opacityMatch[0].replace(')', ''));
            }
        }

        return {
            type: 'outer',
            angle: Math.round(angle),
            blur: blur * 0.75,
            color: colorMatch ? rgbToHex(colorMatch[0]) : '000000',
            offset: offset,
            opacity
        };
    };

    // Parse inline formatting tags
    const parseInlineFormatting = (element, baseOptions = {}, runs = [], baseTextTransform = (x) => x) => {
        let prevNodeIsText = false;

        element.childNodes.forEach((node) => {
            let textTransform = baseTextTransform;

            const isText = node.nodeType === Node.TEXT_NODE || node.tagName === 'BR';
            if (isText) {
                const text = node.tagName === 'BR' ? '\n' : textTransform(node.textContent.replace(/\s+/g, ' '));
                const prevRun = runs[runs.length - 1];
                if (prevNodeIsText && prevRun) {
                    prevRun.text += text;
                } else {
                    runs.push({ text, options: { ...baseOptions } });
                }

            } else if (node.nodeType === Node.ELEMENT_NODE && node.textContent.trim()) {
                const options = { ...baseOptions };
                const computed = window.getComputedStyle(node);

                if (node.tagName === 'SPAN' || node.tagName === 'B' || node.tagName === 'STRONG' || node.tagName === 'I' || node.tagName === 'EM' || node.tagName === 'U' || node.tagName === 'A') {
                    const isBold = computed.fontWeight === 'bold' || parseInt(computed.fontWeight) >= 600;
                    if (isBold && !shouldSkipBold(computed.fontFamily)) options.bold = true;
                    if (computed.fontStyle === 'italic') options.italic = true;
                    if (computed.textDecoration && computed.textDecoration.includes('underline')) options.underline = true;
                    if (computed.color && computed.color !== 'rgb(0, 0, 0)') {
                        options.color = rgbToHex(computed.color);
                        const transparency = extractAlpha(computed.color);
                        if (transparency !== null) options.transparency = transparency;
                    }
                    if (computed.fontSize) options.fontSize = pxToPoints(computed.fontSize);

                    if (node.tagName === 'A') {
                        const href = node.getAttribute('href');
                        if (href) {
                            options.hyperlink = { url: href };
                            if (options.underline === undefined) options.underline = true;
                        }
                    }

                    if (computed.textTransform && computed.textTransform !== 'none') {
                        const transformStr = computed.textTransform;
                        textTransform = (text) => applyTextTransform(text, transformStr);
                    }

                    if (computed.marginLeft && parseFloat(computed.marginLeft) > 0) {
                        errors.push(`Inline element <${node.tagName.toLowerCase()}> has margin-left which is not supported in PowerPoint. Remove margin from inline elements.`);
                    }
                    if (computed.marginRight && parseFloat(computed.marginRight) > 0) {
                        errors.push(`Inline element <${node.tagName.toLowerCase()}> has margin-right which is not supported in PowerPoint. Remove margin from inline elements.`);
                    }
                    if (computed.marginTop && parseFloat(computed.marginTop) > 0) {
                        errors.push(`Inline element <${node.tagName.toLowerCase()}> has margin-top which is not supported in PowerPoint. Remove margin from inline elements.`);
                    }
                    if (computed.marginBottom && parseFloat(computed.marginBottom) > 0) {
                        errors.push(`Inline element <${node.tagName.toLowerCase()}> has margin-bottom which is not supported in PowerPoint. Remove margin from inline elements.`);
                    }

                    parseInlineFormatting(node, options, runs, textTransform);
                }
            }

            prevNodeIsText = isText;
        });

        if (runs.length > 0) {
            runs[0].text = runs[0].text.replace(/^\s+/, '');
            runs[runs.length - 1].text = runs[runs.length - 1].text.replace(/\s+$/, '');
        }

        return runs.filter(r => r.text.length > 0);
    };

    const body = document.body;
    const bodyStyle = window.getComputedStyle(body);
    const backgroundImage = bodyStyle.backgroundImage;
    const backgroundColor = bodyStyle.backgroundColor;

    const errors = [];

    if (backgroundImage && (backgroundImage.includes('linear-gradient') || backgroundImage.includes('radial-gradient'))) {
        errors.push(
            'CSS gradients are not supported. Use Sharp to rasterize gradients as PNG images first, ' +
            'then reference with background-image: url(\'gradient.png\')'
        );
    }

    let background;
    if (backgroundImage && backgroundImage !== 'none') {
        const urlMatch = backgroundImage.match(/url\(["']?([^"')]+)["']?\)/);
        if (urlMatch) {
            background = {
                type: 'image',
                path: urlMatch[1]
            };
        } else {
            background = {
                type: 'color',
                value: rgbToHex(backgroundColor)
            };
        }
    } else {
        background = {
            type: 'color',
            value: rgbToHex(backgroundColor)
        };
    }

    const elements = [];
    const placeholders = [];
    const textTags = ['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'UL', 'OL', 'LI'];
    const processed = new Set();

    document.querySelectorAll('*').forEach((element) => {
        if (processed.has(element)) return;

        if (textTags.includes(element.tagName)) {
            const computed = window.getComputedStyle(element);
            const hasBg = computed.backgroundColor && computed.backgroundColor !== 'rgba(0, 0, 0, 0)';
            const hasBorder = (computed.borderWidth && parseFloat(computed.borderWidth) > 0) ||
                (computed.borderTopWidth && parseFloat(computed.borderTopWidth) > 0) ||
                (computed.borderRightWidth && parseFloat(computed.borderRightWidth) > 0) ||
                (computed.borderBottomWidth && parseFloat(computed.borderBottomWidth) > 0) ||
                (computed.borderLeftWidth && parseFloat(computed.borderLeftWidth) > 0);
            const hasShadow = computed.boxShadow && computed.boxShadow !== 'none';

            if (hasBg || hasBorder || hasShadow) {
                errors.push(
                    `Text element <${element.tagName.toLowerCase()}> has ${hasBg ? 'background' : hasBorder ? 'border' : 'shadow'}. ` +
                    'Backgrounds, borders, and shadows are only supported on <div> elements, not text elements.'
                );
                return;
            }
        }

        if (element.className && element.className.includes('placeholder')) {
            const rect = element.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) {
                errors.push(
                    `Placeholder "${element.id || 'unnamed'}" has ${rect.width === 0 ? 'width: 0' : 'height: 0'}. Check the layout CSS.`
                );
            } else {
                placeholders.push({
                    id: element.id || `placeholder-${placeholders.length}`,
                    x: pxToInch(rect.left),
                    y: pxToInch(rect.top),
                    w: pxToInch(rect.width),
                    h: pxToInch(rect.height)
                });
            }
            processed.add(element);
            return;
        }

        if (element.tagName === 'IMG') {
            const rect = element.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                const computed = window.getComputedStyle(element);
                elements.push({
                    type: 'image',
                    src: element.src,
                    className: element.className || '',
                    style: {
                        objectFit: computed.objectFit || null,
                        objectPosition: computed.objectPosition || null,
                    },
                    position: {
                        x: pxToInch(rect.left),
                        y: pxToInch(rect.top),
                        w: pxToInch(rect.width),
                        h: pxToInch(rect.height)
                    }
                });
                processed.add(element);
                return;
            }
        }

        const isContainer = element.tagName === 'DIV' && !textTags.includes(element.tagName);
        if (isContainer) {
            const computed = window.getComputedStyle(element);
            const hasBg = computed.backgroundColor && computed.backgroundColor !== 'rgba(0, 0, 0, 0)';

            for (const node of element.childNodes) {
                if (node.nodeType === Node.TEXT_NODE) {
                    const text = node.textContent.trim();
                    if (text) {
                        errors.push(
                            `DIV element contains unwrapped text "${text.substring(0, 50)}${text.length > 50 ? '...' : ''}". ` +
                            'All text must be wrapped in <p>, <h1>-<h6>, <ul>, or <ol> tags to appear in PowerPoint.'
                        );
                    }
                }
            }

            const bgImage = computed.backgroundImage;
            if (bgImage && bgImage !== 'none') {
                errors.push(
                    'Background images on DIV elements are not supported. ' +
                    'Use solid colors or borders for shapes, or use slide.addImage() in PptxGenJS to layer images.'
                );
                return;
            }

            const borderTop = computed.borderTopWidth;
            const borderRight = computed.borderRightWidth;
            const borderBottom = computed.borderBottomWidth;
            const borderLeft = computed.borderLeftWidth;
            const borders = [borderTop, borderRight, borderBottom, borderLeft].map(b => parseFloat(b) || 0);
            const hasBorder = borders.some(b => b > 0);
            const hasUniformBorder = hasBorder && borders.every(b => b === borders[0]);
            const borderLines = [];

            if (hasBorder && !hasUniformBorder) {
                const rect = element.getBoundingClientRect();
                const x = pxToInch(rect.left);
                const y = pxToInch(rect.top);
                const w = pxToInch(rect.width);
                const h = pxToInch(rect.height);

                if (parseFloat(borderTop) > 0) {
                    const widthPt = pxToPoints(borderTop);
                    const inset = (widthPt / 72) / 2;
                    borderLines.push({
                        type: 'line',
                        x1: x, y1: y + inset, x2: x + w, y2: y + inset,
                        width: widthPt,
                        color: rgbToHex(computed.borderTopColor)
                    });
                }
                if (parseFloat(borderRight) > 0) {
                    const widthPt = pxToPoints(borderRight);
                    const inset = (widthPt / 72) / 2;
                    borderLines.push({
                        type: 'line',
                        x1: x + w - inset, y1: y, x2: x + w - inset, y2: y + h,
                        width: widthPt,
                        color: rgbToHex(computed.borderRightColor)
                    });
                }
                if (parseFloat(borderBottom) > 0) {
                    const widthPt = pxToPoints(borderBottom);
                    const inset = (widthPt / 72) / 2;
                    borderLines.push({
                        type: 'line',
                        x1: x, y1: y + h - inset, x2: x + w, y2: y + h - inset,
                        width: widthPt,
                        color: rgbToHex(computed.borderBottomColor)
                    });
                }
                if (parseFloat(borderLeft) > 0) {
                    const widthPt = pxToPoints(borderLeft);
                    const inset = (widthPt / 72) / 2;
                    borderLines.push({
                        type: 'line',
                        x1: x + inset, y1: y, x2: x + inset, y2: y + h,
                        width: widthPt,
                        color: rgbToHex(computed.borderLeftColor)
                    });
                }
            }

            if (hasBg || hasBorder) {
                const rect = element.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    const shadow = parseBoxShadow(computed.boxShadow);

                    if (hasBg || hasUniformBorder) {
                        elements.push({
                            type: 'shape',
                            text: '',
                            position: {
                                x: pxToInch(rect.left),
                                y: pxToInch(rect.top),
                                w: pxToInch(rect.width),
                                h: pxToInch(rect.height)
                            },
                            shape: {
                                fill: hasBg ? rgbToHex(computed.backgroundColor) : null,
                                transparency: hasBg ? extractAlpha(computed.backgroundColor) : null,
                                line: hasUniformBorder ? {
                                    color: rgbToHex(computed.borderColor),
                                    width: pxToPoints(computed.borderWidth)
                                } : null,
                                rectRadius: (() => {
                                    const radius = computed.borderRadius;
                                    const radiusValue = parseFloat(radius);
                                    if (radiusValue === 0) return 0;

                                    if (radius.includes('%')) {
                                        if (radiusValue >= 50) return 1;
                                        const minDim = Math.min(rect.width, rect.height);
                                        return (radiusValue / 100) * pxToInch(minDim);
                                    }

                                    if (radius.includes('pt')) return radiusValue / 72;
                                    return radiusValue / PX_PER_IN;
                                })(),
                                shadow: shadow
                            }
                        });
                    }

                    elements.push(...borderLines);
                    processed.add(element);
                    return;
                }
            }
        }

        if (element.tagName === 'UL' || element.tagName === 'OL') {
            const rect = element.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return;

            const liElements = Array.from(element.querySelectorAll('li'));
            const items = [];
            const ulComputed = window.getComputedStyle(element);
            const ulPaddingLeftPt = pxToPoints(ulComputed.paddingLeft);

            const marginLeft = ulPaddingLeftPt * 0.5;
            const textIndent = ulPaddingLeftPt * 0.5;

            liElements.forEach((li, idx) => {
                const isLast = idx === liElements.length - 1;
                const runs = parseInlineFormatting(li, { breakLine: false });
                if (runs.length > 0) {
                    runs[0].text = runs[0].text.replace(/^[•\-\*▪▸]\s*/, '');
                    runs[0].options.bullet = { indent: textIndent };
                }
                if (runs.length > 0 && !isLast) {
                    runs[runs.length - 1].options.breakLine = true;
                }
                items.push(...runs);
            });

            const computed = window.getComputedStyle(liElements[0] || element);

            elements.push({
                type: 'list',
                items: items,
                position: {
                    x: pxToInch(rect.left),
                    y: pxToInch(rect.top),
                    w: pxToInch(rect.width),
                    h: pxToInch(rect.height)
                },
                style: {
                    fontSize: pxToPoints(computed.fontSize),
                    fontFace: computed.fontFamily.split(',')[0].replace(/['"]/g, '').trim(),
                    color: rgbToHex(computed.color),
                    transparency: extractAlpha(computed.color),
                    align: computed.textAlign === 'start' ? 'left' : computed.textAlign,
                    lineSpacing: computed.lineHeight && computed.lineHeight !== 'normal' ? pxToPoints(computed.lineHeight) : null,
                    paraSpaceBefore: 0,
                    paraSpaceAfter: pxToPoints(computed.marginBottom),
                    margin: [marginLeft, 0, 0, 0]
                }
            });

            liElements.forEach(li => processed.add(li));
            processed.add(element);
            return;
        }

        if (!textTags.includes(element.tagName)) return;

        const rect = element.getBoundingClientRect();
        const text = element.textContent.trim();
        if (rect.width === 0 || rect.height === 0 || !text) return;

        if (element.tagName !== 'LI' && /^[•\-\*▪▸○●◆◇■□]\s/.test(text.trimStart())) {
            errors.push(
                `Text element <${element.tagName.toLowerCase()}> starts with bullet symbol "${text.substring(0, 20)}...". ` +
                'Use <ul> or <ol> lists instead of manual bullet symbols.'
            );
            return;
        }

        const computed = window.getComputedStyle(element);
        const rotation = getRotation(computed.transform, computed.writingMode);
        const { x, y, w, h } = getPositionAndSize(element, rect, rotation);

        const baseStyle = {
            fontSize: pxToPoints(computed.fontSize),
            fontFace: computed.fontFamily.split(',')[0].replace(/['"]/g, '').trim(),
            color: rgbToHex(computed.color),
            align: computed.textAlign === 'start' ? 'left' : computed.textAlign,
            lineSpacing: pxToPoints(computed.lineHeight),
            paraSpaceBefore: pxToPoints(computed.marginTop),
            paraSpaceAfter: pxToPoints(computed.marginBottom),
            margin: [
                pxToPoints(computed.paddingLeft),
                pxToPoints(computed.paddingRight),
                pxToPoints(computed.paddingBottom),
                pxToPoints(computed.paddingTop)
            ]
        };

        const transparency = extractAlpha(computed.color);
        if (transparency !== null) baseStyle.transparency = transparency;

        if (rotation !== null) baseStyle.rotate = rotation;

        const hasFormatting = element.querySelector('b, i, u, strong, em, span, a, br');

        if (hasFormatting) {
            const transformStr = computed.textTransform;
            const isBold = computed.fontWeight === 'bold' || parseInt(computed.fontWeight) >= 600;

            // IMPORTANT:
            // If the element contains <br> (including ones inserted during renderer-side wrapping),
            // we still want to preserve the element's base styling for all runs.
            const baseRunOptions = {
                fontSize: baseStyle.fontSize,
                fontFace: baseStyle.fontFace,
                color: baseStyle.color,
                bold: isBold && !shouldSkipBold(computed.fontFamily),
                italic: computed.fontStyle === 'italic',
                underline: computed.textDecoration.includes('underline')
            };
            if (baseStyle.transparency !== undefined) baseRunOptions.transparency = baseStyle.transparency;

            const runs = parseInlineFormatting(element, baseRunOptions, [], (str) => applyTextTransform(str, transformStr));

            const adjustedStyle = { ...baseStyle };
            if (adjustedStyle.lineSpacing) {
                const maxFontSize = Math.max(
                    adjustedStyle.fontSize,
                    ...runs.map(r => r.options?.fontSize || 0)
                );
                if (maxFontSize > adjustedStyle.fontSize) {
                    const lineHeightMultiplier = adjustedStyle.lineSpacing / adjustedStyle.fontSize;
                    adjustedStyle.lineSpacing = maxFontSize * lineHeightMultiplier;
                }
            }

            elements.push({
                type: element.tagName.toLowerCase(),
                text: runs,
                position: { x: pxToInch(x), y: pxToInch(y), w: pxToInch(w), h: pxToInch(h) },
                style: adjustedStyle
            });
        } else {
            const textTransform = computed.textTransform;
            const transformedText = applyTextTransform(text, textTransform);

            const isBold = computed.fontWeight === 'bold' || parseInt(computed.fontWeight) >= 600;

            elements.push({
                type: element.tagName.toLowerCase(),
                text: transformedText,
                position: { x: pxToInch(x), y: pxToInch(y), w: pxToInch(w), h: pxToInch(h) },
                style: {
                    ...baseStyle,
                    bold: isBold && !shouldSkipBold(computed.fontFamily),
                    italic: computed.fontStyle === 'italic',
                    underline: computed.textDecoration.includes('underline')
                }
            });
        }

        processed.add(element);
    });

    return { background, elements, placeholders, errors };
};

async function extractSlideData(page) {
    return await page.evaluate(getSlideDataFromDom);
}

module.exports = {
    getBodyDimensions,
    extractSlideData
};
