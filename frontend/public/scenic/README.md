# Attraction photographs and enhanced card covers

All 16 attraction card covers now use the files in `enhanced/`. The 15 remaining covers were individually enhanced on 2026-10-17 using the built-in image editing tool; Wenchang Pavilion retains its previously approved enhancement. The final browser assets are JPEG quality 90, with the generated pixel dimensions retained (1254×1254 for square originals, 1448×1086 for the other restored covers, and 1747×900 for Wenchang Pavilion). The full-resolution generated PNG files remain in the image tool's output directory.

`../../src/data/scenicCoverImages.json` maps each attraction to its local display file, original image URL, source page and focal position. The original official catalog remains unchanged by this enhancement process and is still used for factual citations. User-supplied originals below are retained unchanged. If an enhanced cover fails to load, the component falls back to its original photo and then the other catalog images.

These are AI-enhanced display images, not documentary originals. Textures, inscriptions, people and other small details may differ from the source; do not use enhanced details as historical or architectural evidence. Original-source attribution does not imply that the source publisher produced or endorsed the enhancement.

## Batch prompts and provenance

See [enhancement-records.json](enhancement-records.json) for the full prompt used for each attraction, its original image URL, source and any targeted correction prompt. No model identifier is asserted beyond the built-in tool's reported execution mode.

## Original supplied photographs and first Wenchang enhancement

- `jade-belt-bridge.jpg`: original user-supplied photograph of Jade Belt Bridge.
- `wenchang-pavilion.jpg`: original user-supplied Wenchang Pavilion photograph (488 × 250), retained unchanged.
- `wenchang-pavilion-enhanced.png`: the first approved AI-enhanced Wenchang photograph, retained as a full-resolution reference. The card now uses its JPEG copy at `enhanced/wenchang-pavilion.jpg`. Created on 2026-10-17 with the built-in image editing tool. Fine textures are AI reconstructions, not independently verified architectural documentation. Use the original photograph for factual detail comparisons.

## Enhancement prompt

Edit target: the attached original 488x250 photograph of Wenchang Pavilion at the Summer Palace, Beijing. Task: faithful high-resolution photo restoration and clarity enhancement for an attraction card on a tourism website. Upscale to a clean high-resolution landscape image, approximately 2048x1056, keeping the original wide composition and camera perspective. Preserve the EXACT existing scene, arrangement, relative scale, roof tiers, pavilion silhouette, white masonry platform, red bridge railings, trees, foreground lotus pond and sky. Recover natural edge clarity and restrained realistic textures in roof tiles, wooden beams, balustrades, masonry and lotus leaves; reduce compression artifacts, pixelation and blur. Natural photographic colors and daylight, not oversaturated, no crunchy sharpening, no HDR. Do not add or remove architecture, people, signage, decorations or new scenic elements. No text, no watermark, no borders. The result should look like the same photograph at higher resolution, not a reinterpretation or newly composed scene.
