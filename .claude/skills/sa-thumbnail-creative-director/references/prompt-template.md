# Prompt Template

Use this prompt structure for actual image generation or for production briefs.

```text
Use case: ads-marketing
Asset type: Naver search ad thumbnail, 640x640 square master with 214x214 crop safety
Product: <insurance product>
Monthly message axis: <SA or Power Content axis>
Scene: <concrete product-fit scene>
Subject: <main person/object, large and centered>
Style/medium: premium 3D animation, polished editorial insurance visual, not photorealistic, not flat icon
Composition/framing: square, central subject readable at small mobile search-ad size, simple background, no crowded details
Lighting/mood: soft natural lighting, calm, trustworthy, not dramatic
Color palette: refined warm-neutral base with one accent color, avoid loud neon or childish pastel
Materials/textures: realistic fabric, glass, paper, metal, home/road/clinic surfaces as relevant
Text: no text, no numbers, no logos, no badges, no readable UI
Constraints: must match the insurance product and selected month; do not copy competitor image composition
Avoid: photorealism, cartoon-child style, disaster sensationalism, injury close-ups, brand marks, text overlays, repeated previous-month scene
```

## Prompt Set Rule

For a four-slot set, vary:

- role;
- scene;
- subject;
- camera distance;
- background;
- dominant object.

Do not create four crops of the same concept unless the user explicitly asks for crop variants.

## Output Brief Fields

For each image, provide:

- slot;
- scene;
- generation prompt;
- avoid list;
- Naver size note;
- crop safety note;
- previous-month variation note;
- review risk.
