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

/**
 * Validate table structure and positioning
 *
 * @param {object} slideData - Extracted slide data containing tables
 * @param {object} bodyDimensions - Body dimensions from scanner
 * @returns {string[]} Array of validation error messages
 */
function validateTables(slideData, bodyDimensions) {
    const errors = [];
    const slideWidthInches = bodyDimensions.width / PX_PER_IN;
    const slideHeightInches = bodyDimensions.height / PX_PER_IN;

    // Extract body padding if available (passed from dom scanner)
    const paddingTop = (bodyDimensions.paddingTop || 0) / PX_PER_IN;
    const paddingRight = (bodyDimensions.paddingRight || 0) / PX_PER_IN;
    const paddingBottom = (bodyDimensions.paddingBottom || 0) / PX_PER_IN;
    const paddingLeft = (bodyDimensions.paddingLeft || 0) / PX_PER_IN;

    // Calculate content area boundaries
    const contentLeft = paddingLeft;
    const contentTop = paddingTop;
    const contentRight = slideWidthInches - paddingRight;
    const contentBottom = slideHeightInches - paddingBottom;

    for (const element of slideData.elements) {
        if (element.type !== 'table') continue;

        // 1. Validate table fits within slide bounds
        const tableLeft = element.position.x;
        const tableTop = element.position.y;
        const tableRight = element.position.x + element.position.w;
        const tableBottom = element.position.y + element.position.h;

        // Check if table extends beyond content area (accounting for padding)
        if (tableRight > contentRight) {
            errors.push(
                `Table extends beyond slide content area by ${(tableRight - contentRight).toFixed(2)}" horizontally ` +
                `(table right edge at ${tableRight.toFixed(2)}", content area ends at ${contentRight.toFixed(2)}"). ` +
                `Reduce table width or adjust positioning.`
            );
        }

        if (tableLeft < contentLeft) {
            errors.push(
                `Table extends beyond slide content area by ${(contentLeft - tableLeft).toFixed(2)}" on the left ` +
                `(table left edge at ${tableLeft.toFixed(2)}", content area starts at ${contentLeft.toFixed(2)}").`
            );
        }

        // Check vertical bounds with 0.3" bottom margin
        const requiredBottomMargin = 0.3;
        const maxBottom = contentBottom - requiredBottomMargin;

        if (tableBottom > maxBottom) {
            errors.push(
                `Table extends too close to bottom edge (table bottom at ${tableBottom.toFixed(2)}", ` +
                `max allowed ${maxBottom.toFixed(2)}" with 0.3" margin). ` +
                `Reduce table height or adjust positioning.`
            );
        }

        if (tableTop < contentTop) {
            errors.push(
                `Table extends beyond slide content area by ${(contentTop - tableTop).toFixed(2)}" at the top ` +
                `(table top edge at ${tableTop.toFixed(2)}", content area starts at ${contentTop.toFixed(2)}").`
            );
        }

        // Also check against absolute slide bounds (belt and suspenders)
        if (tableRight > slideWidthInches) {
            errors.push(
                `Table extends beyond absolute slide width by ${(tableRight - slideWidthInches).toFixed(2)}".`
            );
        }

        if (tableBottom > slideHeightInches) {
            errors.push(
                `Table extends beyond absolute slide height by ${(tableBottom - slideHeightInches).toFixed(2)}".`
            );
        }

        // 2. Validate table has rows
        if (!element.rows || element.rows.length === 0) {
            errors.push(`Table is empty - no rows found.`);
            continue;
        }

        // 3. Validate consistent column count
        const firstRowCellCount = element.rows[0].length;
        element.rows.forEach((row, idx) => {
            // Account for colspan: sum up the effective columns
            const effectiveColumns = row.reduce((sum, cell) => {
                return sum + (cell.options?.colspan || 1);
            }, 0);

            if (idx === 0) return; // Skip first row comparison

            // Allow some flexibility for rowspan/colspan combinations
            // Just warn if significantly different
            if (Math.abs(effectiveColumns - firstRowCellCount) > 2) {
                errors.push(
                    `Table row ${idx + 1} has inconsistent column count ` +
                    `(${effectiveColumns} vs ${firstRowCellCount} in first row). ` +
                    `Check colspan/rowspan usage.`
                );
            }
        });

        // 4. Validate cell text isn't too long (PowerPoint limitations)
        element.rows.forEach((row, rowIdx) => {
            row.forEach((cell, cellIdx) => {
                const cellText = typeof cell.text === 'string'
                    ? cell.text
                    : Array.isArray(cell.text)
                        ? cell.text.map(r => r.text).join('')
                        : '';

                if (cellText.length > 5000) {
                    errors.push(
                        `Table cell at row ${rowIdx + 1}, column ${cellIdx + 1} ` +
                        `contains ${cellText.length} characters (max recommended: 5000). ` +
                        `Consider splitting content.`
                    );
                }
            });
        });

        // 5. Validate rowspan/colspan values are reasonable
        element.rows.forEach((row, rowIdx) => {
            row.forEach((cell, cellIdx) => {
                const colspan = cell.options?.colspan;
                const rowspan = cell.options?.rowspan;

                if (colspan && colspan > firstRowCellCount) {
                    errors.push(
                        `Table cell at row ${rowIdx + 1}, column ${cellIdx + 1} ` +
                        `has colspan=${colspan} but table only has ${firstRowCellCount} columns.`
                    );
                }

                if (rowspan && rowspan > element.rows.length) {
                    errors.push(
                        `Table cell at row ${rowIdx + 1}, column ${cellIdx + 1} ` +
                        `has rowspan=${rowspan} but table only has ${element.rows.length} rows.`
                    );
                }
            });
        });
    }

    return errors;
}

module.exports = {
    validateDimensions,
    validateTextBoxPosition,
    wrapAndValidateTitles,
    validateTables
};
