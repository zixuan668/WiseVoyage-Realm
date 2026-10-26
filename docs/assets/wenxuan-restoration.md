# 文轩图片修复记录

2026-10-24 透明背景版本：`static/digital_guide/covers/wenxuan-transparent.png`。
使用内置 imagegen 编辑工具，输入清晰版人物图，移除白色背景并保留 PNG 的 RGBA 通道；原图保留，文轩展示图指向透明版本。图像检查包括透明角落、白衬衫和浅色裤子的不透明区域。

透明版本最终提示词：

Use case: background-extraction. Input image 1 is the exact edit target: the existing digital guide Wenxuan portrait asset. Remove ONLY the entire white/light-gray background and produce a clean, genuinely transparent RGBA PNG cutout. Preserve the same person exactly: recognizable face and expression, black hairstyle including fine hair strands, blue three-piece suit and fabric texture, light blue shirt, striped red/blue tie, light gray trousers, hands, proportions, lighting, front-facing standing pose, full subject outline, scale, and head-to-upper-thigh crop. Preserve the light gray trousers and white shirt/cuffs as fully opaque foreground. Preserve the current framing and canvas proportions. Do not redraw, beautify, recolor, sharpen or modify the man. Remove white background both around the outer silhouette and in the gaps between his arms and torso. Edges must be clean with antialiased alpha and no white halo. No replacement background, no floor, no shadows behind the subject, no text, no additional objects.

使用内置 image_gen 编辑工具。原始图片保留，当前本地数据库的文轩展示图已指向清晰版。

- 原图：`static/product_files/images/1791628955__b22e900eba36423ebc7a04fc172941f9.png`，177 × 213。
- 修复图：`static/digital_guide/covers/wenxuan-restored.png`，1144 × 1375。
- 人物、蓝色西服、领带、站姿与浅色背景作为编辑约束；细节由生成式修复重建。

最终编辑提示词：

Use case: identity-preserve. Asset type: restored portrait for the existing digital guide Wenxuan in an application. Input image 1 is the exact edit target, a low-resolution 177x213 portrait of an East Asian male 3D digital human. Restore and upscale THIS image to a crisp high-resolution portrait (about 4x or greater), removing blur, compression and jagged edges. Preserve the same recognizable face, hairstyle, age, expression, body proportions, centered front-facing standing pose with arms down, blue three-piece suit, light blue shirt, red/blue striped tie and light gray trousers. Preserve the same existing crop from above his head to upper thighs, subject scale and clean very light gray/white background. Do not redesign the character or change clothing, pose or composition. Recover natural-looking facial features, hair strands and suit seams/fabric with restrained detail consistent with the original semi-realistic 3D avatar style. No face beautification, no new objects, no logos, no text, no borders. Output a single standalone restored portrait image; this is an asset edit, not a webpage mockup.
