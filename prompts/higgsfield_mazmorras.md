# Prompts de Higgsfield: escenarios de mazmorra, lobby y ciudad

Modelo: `nano_banana_2`, 1k, 1:1, ~1,5 créditos por imagen.
Referencia de estilo en todas: `assets/colegio/props.png` (pack comprado "Traditional School
Asset pack"), pasada con `--image`. Presupuesto aprobado por Sofia el 10 nov 2026: hasta 40 cr.

Las imágenes generadas **no se usan enteras como fondo**. Se procesan con
`tools/procesar_higgsfield.py`:
- hojas de objetos sobre verde → un PNG transparente por objeto (`props`);
- texturas → baldosa repetible a resolución de pixel art (`textura`).

## Bloque de estilo (se antepone a cada prompt)

> 2D pixel art game asset, top-down 3/4 view (camera looking down at about 60 degrees, front
> faces visible), same style as the reference image: chunky pixels, dark 1-pixel outline,
> soft top-left light, muted desaturated colors with a slight cool night tint. No text, no
> letters, no logos, no UI, no characters, no people.

## Hojas de objetos (fondo verde)

Sufijo común:

> Arranged as a sprite sheet on a flat pure chroma green background (#00FF00), each object
> separate with wide empty green space between them, no shadows touching other objects, no
> ground, no floor. Objects in 2 or 3 rows, read left to right.

| Archivo | Objetos en orden de lectura |
|---|---|
| `colegio_biblioteca` | tall wooden bookshelf full of books; wide library reading table; globe on a stand; stack of books; wooden lab bench with test tubes; rolling whiteboard with blank board; potted ficus; cardboard box of papers |
| `hospital_a` | hospital bed with white sheets and metal frame (viewed from above, long); medical cabinet with glass doors; vital signs monitor on a rolling stand; IV drip stand with bag; folding privacy screen of pale teal fabric; wheelchair |
| `hospital_b` | lab bench with microscope and vials; waiting room row of three plastic chairs; medical supply cart with drawers; red biohazard bin; reception counter; potted plant in white pot; oxygen tank pair; small medicine fridge |
| `medios_a` | office desk with two computer monitors and keyboard; studio broadcast camera on tripod; studio softbox light on stand; news anchor desk curved; server rack with blinking lights; office swivel chair |
| `medios_b` | large flat TV screen on stand (screen glowing blue, blank); microphone on boom stand; tangled cable bundle; office water cooler; stack of equipment flight cases; potted plant; printer; ring light on tripod |
| `alcaldia_a` | stone classical column with capital (tall); bronze bust on marble pedestal; long polished wooden council table; ornate high-back chair; wooden lectern podium; brass stanchion pair with red velvet rope |
| `alcaldia_b` | marble bench; potted palm in stone urn; filing cabinet with papers spilling out, glowing magenta cracks; corrupted server terminal glowing magenta; ballot box; red carpet runner piece (short); flag stand with blank deep blue flag; cracked marble block with magenta glitch light |
| `ciudad_props` | street bench; newsstand kiosk (no text); bus stop shelter (blank panels); trash bin; fire hydrant; potted street planter with shrub; street lamp short; vending machine glowing (blank) |
| `lobby_props` | hotel lobby armchair; low coffee table; potted plant tall; luggage cart; reception bell on small stand; floor lamp warm; rug square; water dispenser |

## Texturas

Sufijo común:

> Seamless tileable texture, perfectly flat top-down orthographic view, fills the entire image
> edge to edge, even lighting, no perspective, no objects, no vignette.

| Archivo | Descripción |
|---|---|
| `hospital_piso` | clean clinical vinyl floor tiles, pale blue-grey 2x2 large square tiles, subtle speckles |
| `hospital_muro` | front-facing hospital wall: pale mint tiled lower half with a teal stripe, white upper wall (wall face, frontal) |
| `medios_piso` | dark charcoal carpet tiles with faint blue grid, office raised floor |
| `medios_muro` | front-facing acoustic foam panels dark navy with thin LED strip (wall face, frontal) |
| `alcaldia_piso` | polished dark marble floor with large checkered slabs, deep purple and charcoal, gold inlay lines |
| `alcaldia_muro` | front-facing government building wall: dark wood wainscoting below, deep red damask wallpaper above (wall face, frontal) |
| `colegio_biblioteca_piso` | worn green linoleum school floor tiles |
