const { PT_PER_PX, PX_PER_IN, EMU_PER_IN } = require('./utils.cjs');

/**
 * Wrap and validate slide titles (H1) so a single line never exceeds a fraction
 * of the slide width. Wrapping is done at whole-word boundaries.
 *
 * This runs in the renderer stage (Playwright page context) so measurements match
 * how the HTML actually renders.
 *
 * @param {import('playwright').Page} page
 * @param {number} maxSlideWidthFraction - e.g. 0.75 for 3/4 slide width
 * @returns {Promise<string[]>}
 */
async function wrapAndValidateTitles(page, maxSlideWidthFraction = 0.75) {
    const result = await page.evaluate(({ maxSlideWidthFraction }) => {
        const errors = [];

        const body = document.body;
        const bodyStyle = window.getComputedStyle(body);
        const slideWidthPx = parseFloat(bodyStyle.width);

        if (!Number.isFinite(slideWidthPx) || slideWidthPx <= 0) {
            errors.push('Unable to determine slide width for title validation.');
            return { errors };
        }

        const maxLineWidthPx = slideWidthPx * maxSlideWidthFraction;
        const tolerancePx = 1.5;

        const measureTextWidthPx = (text, computedStyle) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            if (!ctx) return null;

            const fontStyle = computedStyle.fontStyle || 'normal';
            const fontVariant = computedStyle.fontVariant || 'normal';
            const fontWeight = computedStyle.fontWeight || 'normal';
            const fontSize = computedStyle.fontSize || '16px';
            const fontFamily = computedStyle.fontFamily || 'sans-serif';
            ctx.font = `${fontStyle} ${fontVariant} ${fontWeight} ${fontSize} ${fontFamily}`;

            return ctx.measureText(text).width;
        };

        const setLinesWithBr = (el, lines) => {
            while (el.firstChild) el.removeChild(el.firstChild);
            lines.forEach((line, idx) => {
                el.appendChild(document.createTextNode(line));
                if (idx < lines.length - 1) el.appendChild(document.createElement('br'));
            });
        };

        const normalizeSpaces = (s) => s.replace(/\s+/g, ' ').trim();

        // Only apply to content/title slides (e.g. main content h1s and summary) and
        // explicitly avoid title slide h1s and ending slides. We detect common templates
        // used by our HTML generators:
        //  - include if: h1 has class "h1", or sits inside a .page or .content container, or has class "summary"
        //  - exclude if: h1 has class "title" or class "ending"/"end"
        const h1s = Array.from(document.querySelectorAll('h1')).filter(h1 => {
            const cls = h1.className || '';
            const hasTitleClass = h1.classList && h1.classList.contains('title');
            const hasEndingClass = h1.classList && (h1.classList.contains('ending') || h1.classList.contains('end'));
            const isContentCandidate = h1.classList && h1.classList.contains('h1') || h1.closest('.page') || h1.closest('.content') || (h1.classList && h1.classList.contains('summary'));
            return isContentCandidate && !hasTitleClass && !hasEndingClass;
        });

        h1s.forEach((h1) => {
            const computed = window.getComputedStyle(h1);
            const rawText = normalizeSpaces(h1.textContent || '');
            if (!rawText) return;

            // If author already inserted explicit breaks, respect them.
            if (h1.querySelector('br') || rawText.includes('\n')) return;

            // Make sure CSS doesn't force a single line.
            if (computed.whiteSpace === 'nowrap') {
                h1.style.whiteSpace = 'normal';
            }

            const words = rawText.split(' ');
            const lines = [];
            let current = '';

            for (const word of words) {
                const candidate = current ? `${current} ${word}` : word;
                const candidateWidth = measureTextWidthPx(candidate, computed);
                if (candidateWidth == null) {
                    // If we can't measure, fail closed.
                    errors.push(`Unable to measure title width for: "${rawText.substring(0, 80)}${rawText.length > 80 ? '…' : ''}"`);
                    return;
                }

                if (candidateWidth <= maxLineWidthPx + tolerancePx) {
                    current = candidate;
                    continue;
                }

                if (!current) {
                    // Single word longer than allowed; cannot wrap by whole words.
                    errors.push(
                        `Title contains a word too long to fit within ${(maxSlideWidthFraction * 100).toFixed(0)}% of slide width: "${word.substring(0, 80)}${word.length > 80 ? '…' : ''}"`
                    );
                    return;
                }

                lines.push(current);
                current = word;
            }

            if (current) lines.push(current);

            // Only modify DOM if wrapping is required.
            if (lines.length > 1) {
                setLinesWithBr(h1, lines);
            }

            // Validate all lines are within limit.
            for (const line of lines) {
                const w = measureTextWidthPx(line, computed);
                if (w != null && w > maxLineWidthPx + tolerancePx) {
                    errors.push(
                        `Title line exceeds ${(maxSlideWidthFraction * 100).toFixed(0)}% slide width after wrapping: "${line.substring(0, 80)}${line.length > 80 ? '…' : ''}"`
                    );
                    return;
                }
            }
        });

        return { errors };
    }, { maxSlideWidthFraction });

    return result?.errors || [];
}

/**
 * Validate dimensions match presentation layout
 */
function validateDimensions(bodyDimensions, presentation) {
    const errors = [];
    const widthInches = bodyDimensions.width / PX_PER_IN;
    const heightInches = bodyDimensions.height / PX_PER_IN;

    if (presentation.presLayout) {
        const layoutWidth = presentation.presLayout.width / EMU_PER_IN;
        const layoutHeight = presentation.presLayout.height / EMU_PER_IN;

        if (Math.abs(layoutWidth - widthInches) > 0.1 || Math.abs(layoutHeight - heightInches) > 0.1) {
            errors.push(
                `HTML dimensions (${widthInches.toFixed(1)}" × ${heightInches.toFixed(1)}") ` +
                `don't match presentation layout (${layoutWidth.toFixed(1)}" × ${layoutHeight.toFixed(1)}")`
            );
        }
    }
    return errors;
}

/**
 * Validate text box positions to ensure margins
 */
function validateTextBoxPosition(slideData, bodyDimensions) {
    const errors = [];
    const slideHeightInches = bodyDimensions.height / PX_PER_IN;
    const minBottomMargin = 0.5; // 0.5 inches from bottom

    for (const element of slideData.elements) {
        // Check text elements (p, h1-h6, list)
        if (['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'list'].includes(element.type)) {
            const fontSize = element.style?.fontSize || 0;
            const bottomEdge = element.position.y + element.position.h;
            const distanceFromBottom = slideHeightInches - bottomEdge;

            if (fontSize > 12 && distanceFromBottom < minBottomMargin) {
                const getText = () => {
                    if (typeof element.text === 'string') return element.text;
                    if (Array.isArray(element.text)) return element.text.find(t => t.text)?.text || '';
                    if (Array.isArray(element.items)) return element.items.find(item => item.text)?.text || '';
                    return '';
                };
                const textPrefix = getText().substring(0, 50) + (getText().length > 50 ? '...' : '');

                errors.push(
                    `Text box "${textPrefix}" ends too close to bottom edge ` +
                    `(${distanceFromBottom.toFixed(2)}" from bottom, minimum ${minBottomMargin}" required)`
                );
            }
        }
    }

    return errors;
}

module.exports = {
    validateDimensions,
    validateTextBoxPosition,
    wrapAndValidateTitles
};
