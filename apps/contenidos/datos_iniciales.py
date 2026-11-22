"""
Contenido inicial de EcoParce, verificado contra la normativa colombiana.
Cada guía cita su fuente oficial (RN-02). Los puntos de entrega de demostración
se marcan como «(ejemplo)» y solo se cargan con la opción --demo.
"""

R2184 = 'Resolución 2184 de 2019, Ministerio de Ambiente y Desarrollo Sostenible (código de colores)'

GUIAS = [
    # slug, título, tipo, contenedor, resumen, cuerpo, fuente
    ('bolsa-blanca-aprovechables', 'Bolsa blanca: aprovechables', 'SEPARACION', 'BLANCA',
     'Plástico, vidrio, metales, multicapa, papel y cartón, siempre limpios y secos.',
     """Lo que va en la bolsa blanca lo recogen los recicladores de oficio y vuelve a la industria como materia prima. Por eso debe ir limpio y seco: un envase con comida o grasa contamina todo lo demás.
+ Botellas, envases y bolsas plásticas
+ Botellas y frascos de vidrio
+ Latas de aluminio y de conservas
+ Cajas de leche y de jugo (envases multicapa o tetrapak)
+ Papel, periódico, revistas, cuadernos y cajas de cartón
- Servilletas, papel higiénico y pañales usados
- Cartón o papel con grasa o restos de comida (como la caja de la pizza)
- Envolturas metalizadas de mecato y paquetes de papas
- Pilas, medicamentos o bombillos: van a un punto posconsumo""", R2184 + ', artículo 4'),
    ('bolsa-negra-no-aprovechables', 'Bolsa negra: no aprovechables', 'SEPARACION', 'NEGRA',
     'Lo que ya no se puede reciclar: papel higiénico, servilletas, papeles y cartones con comida.',
     """La bolsa negra va al relleno sanitario. Úsala solo para lo que de verdad no se puede aprovechar, así reducimos lo que se entierra.
+ Papel higiénico, servilletas y toallas de cocina usadas
+ Pañales y toallas higiénicas
+ Tapabocas y guantes desechables
+ Papeles y cartones con grasa o restos de comida
+ Envolturas metalizadas de mecato, colillas y barrido
- Envases plásticos o de vidrio limpios: van en la bolsa blanca
- Restos de comida y cáscaras: van en la bolsa verde
- Pilas, aceite y medicamentos: van a un punto posconsumo""", R2184 + ', artículo 4'),
    ('bolsa-verde-organicos', 'Bolsa verde: orgánicos aprovechables', 'SEPARACION', 'VERDE',
     'Restos de comida, cáscaras y desechos agrícolas que se pueden convertir en abono.',
     """Los residuos orgánicos son casi la mitad de la basura de un hogar. Bien separados se pueden transformar en abono o compost.
+ Restos de comida cruda o cocinada
+ Cáscaras de frutas, verduras y huevo
+ Cuncho de café y residuos de aromáticas
+ Hojas secas, pasto y residuos de jardín
- Servilletas sucias o papel higiénico: van en la bolsa negra
- Bolsas plásticas, aunque tengan comida
- Aceite de cocina usado: va a un punto de recolección""", R2184 + ', artículo 4'),
    ('como-sacar-la-basura', 'Cómo sacar la basura en casa', 'MANEJO', None,
     'Buenas prácticas para entregar los residuos y no ensuciar el andén.',
     """Separar en casa es la mitad del trabajo; la otra mitad es entregar bien los residuos al servicio de aseo y a los recicladores.
+ Saca las bolsas solo en el día y la hora de recolección de tu sector
+ Cierra bien cada bolsa con un nudo para que no se riegue
+ Deja la bolsa blanca aparte para que el reciclador la reconozca
+ Aplasta botellas, latas y cajas para que ocupen menos espacio
- No dejes bolsas en el andén fuera del horario de recolección
- No mezcles residuos especiales con la basura de las bolsas
- No quemes ni entierres basura: contamina el aire y el suelo""",
     'Decreto 1077 de 2015 (servicio público de aseo) y ' + R2184),
    ('reducir-y-reutilizar', 'Antes de botar: reduce y reutiliza', 'MANEJO', None,
     'La mejor basura es la que no se produce. Ideas sencillas para generar menos residuos.',
     """Reciclar ayuda, pero reducir y reutilizar ayuda más: cada envase que no compras es uno menos que separar.
+ Lleva tu propia bolsa de tela al mercado
+ Usa termo o botella reutilizable en lugar de botellas desechables
+ Compra a granel o en presentaciones grandes cuando puedas
+ Repara antes de reemplazar: ropa, zapatos y electrodomésticos
- Evita los cubiertos, pitillos y vasos desechables
- No botes lo que otro puede usar: dona ropa, libros y juguetes""",
     'Política Nacional para la Gestión Integral de Residuos Sólidos (CONPES 3874 de 2016)'),
    ('pilas-y-baterias', 'Pilas y baterías', 'ESPECIAL', 'POSCONSUMO',
     'Las pilas tienen metales que contaminan el agua y el suelo. Nunca van en ninguna bolsa.',
     """Las pilas usadas se recogen en contenedores especiales de los programas posconsumo, ubicados en supermercados, centros comerciales y universidades.
+ Guárdalas en un frasco o caja seca y cerrada
+ Cubre con cinta los polos de las baterías de litio
+ Llévalas a un contenedor posconsumo de pilas
- No las botes en ninguna bolsa
- No las abras, perfores ni quemes""",
     'Resolución 1297 de 2010, Ministerio de Ambiente (sistemas de recolección de pilas y acumuladores)'),
    ('medicamentos-vencidos', 'Medicamentos vencidos', 'ESPECIAL', 'POSCONSUMO',
     'Los medicamentos vencidos o que ya no usas se entregan en puntos de recolección de droguerías.',
     """Los medicamentos tienen principios activos que no deben llegar al agua ni al relleno sanitario.
+ Entrégalos en su empaque original en un contenedor posconsumo de medicamentos
+ Los jarabes van con su frasco bien tapado
- No los botes al inodoro ni al lavaplatos
- No los mezcles con la basura
- Las agujas y jeringas no van en estos contenedores: pregunta en tu EPS o droguería""",
     'Resolución 371 de 2009, Ministerio de Ambiente (posconsumo de fármacos o medicamentos vencidos)'),
    ('aparatos-electricos-y-electronicos', 'Aparatos eléctricos y electrónicos', 'ESPECIAL', 'POSCONSUMO',
     'Celulares, computadores, cargadores y pequeños electrodomésticos son RAEE: tienen materiales valiosos y peligrosos.',
     """Los residuos de aparatos eléctricos y electrónicos (RAEE) se recuperan en programas posconsumo y jornadas de recolección.
+ Borra tus datos personales del celular o computador antes de entregarlo
+ Entrégalo completo, sin desarmarlo
+ Lleva cargadores y cables junto con el aparato
- No los botes en ninguna bolsa
- No los desarmes para sacar piezas""",
     'Ley 1672 de 2013 (gestión integral de residuos de aparatos eléctricos y electrónicos)'),
    ('bombillos', 'Bombillos', 'ESPECIAL', 'POSCONSUMO',
     'Los bombillos ahorradores y los tubos fluorescentes contienen mercurio.',
     """Un bombillo fluorescente roto libera vapor de mercurio. Por eso se entrega entero en un punto de recolección.
+ Guárdalo en su caja original o envuelto en papel
+ Llévalo a un contenedor posconsumo de bombillas
- No lo rompas ni lo botes en ninguna bolsa
- Si se rompe, ventila el lugar y recoge los restos con guantes""",
     'Resolución 1511 de 2010, Ministerio de Ambiente (recolección selectiva de bombillas)'),
    ('aceite-de-cocina-usado', 'Aceite de cocina usado', 'ESPECIAL', 'POSCONSUMO',
     'Un litro de aceite usado puede contaminar miles de litros de agua. Guárdalo y entrégalo.',
     """El aceite de cocina usado se puede transformar en biocombustible si se entrega a un gestor autorizado.
+ Déjalo enfriar y cuélalo
+ Guárdalo en una botella plástica bien tapada
+ Entrégalo en un punto de recolección de aceite usado
- No lo eches al lavaplatos, al inodoro ni al sifón
- No lo mezcles con la basura ni con la bolsa verde""",
     'Resolución 316 de 2018, Ministerio de Ambiente (gestión de aceites de cocina usados)'),
]

RESIDUOS = [
    # nombre, sinónimos, contenedor, slug de guía, preparación
    ('Botella plástica', 'botella pet, botella de gaseosa, botella de agua, envase plástico, botella', 'BLANCA', 'bolsa-blanca-aprovechables', 'vacíala y enjuágala; déjala seca; aplástala para que ocupe menos'),
    ('Bolsa plástica', 'bolsa de supermercado, bolsa de mercado, bolsa', 'BLANCA', 'bolsa-blanca-aprovechables', 'sacúdela para que quede limpia; dóblala o mételas todas en una sola bolsa'),
    ('Envase de yogur', 'vaso de yogur, vasito plástico, tarrina', 'BLANCA', 'bolsa-blanca-aprovechables', 'enjuágalo; déjalo seco'),
    ('Envase de champú', 'frasco de champú, envase de detergente, envase de jabón, frasco plástico', 'BLANCA', 'bolsa-blanca-aprovechables', 'vacíalo y enjuágalo; ponle la tapa'),
    ('Tapa plástica', 'tapa de botella, tapas, tapitas', 'BLANCA', 'bolsa-blanca-aprovechables', 'déjala limpia y seca'),
    ('Lata de aluminio', 'lata de gaseosa, lata de cerveza, lata', 'BLANCA', 'bolsa-blanca-aprovechables', 'vacíala; aplástala'),
    ('Lata de conservas', 'lata de atún, lata de sardinas, enlatado, lata de comida', 'BLANCA', 'bolsa-blanca-aprovechables', 'enjuágala para quitar el aceite y la comida; déjala seca; cuidado con los bordes filosos'),
    ('Botella de vidrio', 'frasco de vidrio, envase de vidrio, vidrio, botella de vino', 'BLANCA', 'bolsa-blanca-aprovechables', 'enjuágala; si está rota, envuélvela en papel y márcala'),
    ('Caja de leche', 'tetrapak, tetra pak, caja de jugo, envase multicapa, multicapa, cajita de jugo', 'BLANCA', 'bolsa-blanca-aprovechables', 'vacíala y enjuágala; ábrela o aplástala; déjala seca'),
    ('Caja de cartón', 'cartón, caja, cajas, carton corrugado', 'BLANCA', 'bolsa-blanca-aprovechables', 'quítale la cinta si puedes; desármala y aplástala; mantenla seca'),
    ('Papel de oficina', 'hojas, papel, fotocopias, cuaderno, papel bond', 'BLANCA', 'bolsa-blanca-aprovechables', 'no lo arrugues; mantenlo seco'),
    ('Periódico', 'revista, papel periódico, folleto, volante', 'BLANCA', 'bolsa-blanca-aprovechables', 'mantenlo seco; amárralo con otros papeles'),
    ('Servilleta usada', 'servilleta, servilletas, toalla de cocina, papel de cocina', 'NEGRA', 'bolsa-negra-no-aprovechables', ''),
    ('Papel higiénico', 'papel higienico usado, papel de baño', 'NEGRA', 'bolsa-negra-no-aprovechables', ''),
    ('Pañal desechable', 'pañal, pañales, toalla higiénica, protector diario', 'NEGRA', 'bolsa-negra-no-aprovechables', 'envuélvelo y ciérralo bien'),
    ('Tapabocas', 'mascarilla, cubrebocas, tapaboca, guantes desechables', 'NEGRA', 'bolsa-negra-no-aprovechables', 'córtale las tiras; mételo en una bolsa cerrada'),
    ('Caja de pizza con grasa', 'cartón con grasa, caja de pizza, cartón sucio, papel con grasa', 'NEGRA', 'bolsa-negra-no-aprovechables', 'si una parte está limpia, córtala y ponla en la bolsa blanca'),
    ('Icopor con comida', 'icopor sucio, bandeja de icopor, poliestireno, plato de icopor', 'NEGRA', 'bolsa-negra-no-aprovechables', 'quita los restos de comida a la bolsa verde'),
    ('Paquete de papas', 'envoltura de mecato, empaque metalizado, paquete de snack, bolsa de papitas, envoltura de dulce', 'NEGRA', 'bolsa-negra-no-aprovechables', ''),
    ('Colilla de cigarrillo', 'colilla, cigarrillo, ceniza', 'NEGRA', 'bolsa-negra-no-aprovechables', 'apágala por completo antes de botarla'),
    ('Barrido', 'polvo, residuos de barrer, mugre', 'NEGRA', 'bolsa-negra-no-aprovechables', ''),
    ('Restos de comida', 'sobras, comida, restos de almuerzo, comida dañada', 'VERDE', 'bolsa-verde-organicos', 'escurre los líquidos; no incluyas servilletas ni bolsas'),
    ('Cáscaras de fruta', 'cáscara de banano, cáscara de naranja, cascaras, cáscara de mango, fruta dañada', 'VERDE', 'bolsa-verde-organicos', ''),
    ('Cáscaras de verdura', 'cáscara de papa, cáscara de cebolla, verdura dañada, tallos', 'VERDE', 'bolsa-verde-organicos', ''),
    ('Cáscara de huevo', 'cascarón, huevo, cáscaras de huevo', 'VERDE', 'bolsa-verde-organicos', ''),
    ('Cuncho de café', 'borra de café, café molido usado, residuo de café, tinto', 'VERDE', 'bolsa-verde-organicos', 'escúrrelo bien'),
    ('Hojas secas y pasto', 'pasto, poda, residuos de jardín, hojas, ramas pequeñas', 'VERDE', 'bolsa-verde-organicos', ''),
    ('Pilas', 'pila, baterías aa, pilas aaa, pila de reloj, pila botón, batería', 'POSCONSUMO', 'pilas-y-baterias', 'guárdalas en un frasco seco y cerrado; llévalas a un contenedor posconsumo de pilas'),
    ('Batería de celular', 'batería de litio, batería recargable, power bank', 'POSCONSUMO', 'pilas-y-baterias', 'cubre los polos con cinta; no la perfores'),
    ('Celular viejo', 'celular, teléfono, celular dañado, smartphone, tablet', 'POSCONSUMO', 'aparatos-electricos-y-electronicos', 'borra tus datos y retira la SIM; entrégalo completo'),
    ('Computador', 'portátil, laptop, computadora, monitor, teclado, mouse', 'POSCONSUMO', 'aparatos-electricos-y-electronicos', 'borra tus datos; entrégalo completo, sin desarmarlo'),
    ('Cargador y cables', 'cargador, cable, cables, audífonos, cable usb', 'POSCONSUMO', 'aparatos-electricos-y-electronicos', 'enróllalos y amárralos'),
    ('Pequeños electrodomésticos', 'licuadora, plancha, secador, sanduchera, radio, electrodoméstico', 'POSCONSUMO', 'aparatos-electricos-y-electronicos', 'entrégalos completos, con su cable'),
    ('Medicamentos vencidos', 'medicamentos, pastillas, jarabe, remedios, pastas, drogas vencidas', 'POSCONSUMO', 'medicamentos-vencidos', 'déjalos en su empaque original; llévalos a un contenedor de medicamentos en droguerías'),
    ('Bombillo ahorrador', 'bombillo, bombilla, lámpara fluorescente, tubo fluorescente, foco', 'POSCONSUMO', 'bombillos', 'guárdalo entero en su caja o envuelto en papel'),
    ('Aceite de cocina usado', 'aceite, aceite usado, aceite de freír', 'POSCONSUMO', 'aceite-de-cocina-usado', 'déjalo enfriar y cuélalo; guárdalo en una botella plástica bien tapada; entrégalo en un punto de recolección'),
]

PREGUNTAS = [
    # enunciado, explicación, dificultad, opciones (texto, correcta)
    ('¿Dónde va una caja de pizza con grasa?', 'El cartón con grasa ya no se puede reciclar: va en la bolsa negra. Si una parte está limpia, esa sí va en la blanca.', 1,
     [('Bolsa blanca', False), ('Bolsa negra', True), ('Bolsa verde', False)]),
    ('¿De qué color es la bolsa para los residuos aprovechables como plástico, vidrio y papel?', 'La bolsa blanca es para los aprovechables, según la Resolución 2184 de 2019.', 1,
     [('Blanca', True), ('Verde', False), ('Negra', False)]),
    ('¿Dónde van las cáscaras de banano?', 'Las cáscaras y los restos de comida son orgánicos aprovechables: van en la bolsa verde.', 1,
     [('Bolsa negra', False), ('Bolsa blanca', False), ('Bolsa verde', True)]),
    ('¿Qué haces con las pilas usadas?', 'Las pilas no van en ninguna bolsa: tienen metales que contaminan. Llévalas a un contenedor posconsumo.', 1,
     [('Las boto en la bolsa negra', False), ('Las llevo a un punto posconsumo', True), ('Las pongo en la bolsa blanca', False), ('Las entierro en una matera', False)]),
    ('¿Cómo debe ir una botella plástica en la bolsa blanca?', 'Vacía, limpia y seca. Con restos de comida o bebida ensucia lo demás y el reciclador no la puede aprovechar.', 1,
     [('Con un poco de gaseosa', False), ('Limpia y seca', True), ('Con la comida que sobró', False)]),
    ('¿Dónde va el papel higiénico usado?', 'El papel higiénico, las servilletas y los pañales usados no son aprovechables: bolsa negra.', 1,
     [('Bolsa blanca, porque es papel', False), ('Bolsa negra', True), ('Bolsa verde', False)]),
    ('¿Qué norma definió el código de colores blanco, negro y verde en Colombia?', 'La Resolución 2184 de 2019 del Ministerio de Ambiente unificó el código de colores desde enero de 2021.', 2,
     [('Resolución 2184 de 2019', True), ('Ley 1581 de 2012', False), ('Resolución 1297 de 2010', False)]),
    ('¿Qué haces con el aceite de cocina usado?', 'Frío, colado y en una botella cerrada, a un punto de recolección. Por el desagüe contamina el agua y tapa las tuberías.', 2,
     [('Lo echo por el lavaplatos con agua caliente', False), ('Lo guardo en una botella cerrada y lo entrego en un punto de recolección', True), ('Lo pongo en la bolsa verde', False)]),
    ('Una caja de leche (tetrapak) limpia va en la...', 'Los envases multicapa limpios son aprovechables: bolsa blanca, abiertos o aplastados.', 2,
     [('Bolsa blanca', True), ('Bolsa negra', False), ('Bolsa verde', False)]),
    ('¿Dónde se entregan los medicamentos vencidos?', 'En los contenedores posconsumo de medicamentos de droguerías y supermercados, en su empaque original.', 2,
     [('En el inodoro', False), ('En un contenedor posconsumo de medicamentos', True), ('En la bolsa negra', False)]),
    ('¿Un tapabocas usado va en la...?', 'Los tapabocas y guantes desechables son no aprovechables: bolsa negra, bien cerrada.', 1,
     [('Bolsa blanca', False), ('Bolsa verde', False), ('Bolsa negra', True)]),
    ('¿Dónde va el cuncho de café?', 'El cuncho o borra de café es orgánico: va en la bolsa verde y sirve para hacer abono.', 1,
     [('Bolsa verde', True), ('Bolsa negra', False), ('Por el lavaplatos', False)]),
    ('¿Qué haces con un celular que ya no sirve?', 'Es un residuo eléctrico y electrónico (RAEE): borra tus datos y entrégalo en un punto posconsumo.', 2,
     [('Lo boto en la bolsa blanca', False), ('Lo entrego en un punto posconsumo de electrónicos', True), ('Lo desarmo y boto las piezas', False)]),
    ('¿Qué debes hacer si se rompe una botella de vidrio que vas a reciclar?', 'El vidrio roto puede herir a los recicladores: envuélvelo bien en papel o cartón, márcalo como «vidrio roto» y ponlo en la bolsa blanca.', 2,
     [('Echarlo suelto en la bolsa blanca', False), ('Envolverlo en papel o cartón, marcarlo y entregarlo aparte en la bolsa blanca', True), ('Botarlo en la bolsa verde', False)]),
    ('¿Dónde va el paquete metalizado de unas papas fritas?', 'Las envolturas metalizadas no son aprovechables según la Resolución 2184: van en la bolsa negra.', 3,
     [('Bolsa blanca', False), ('Bolsa negra', True), ('Bolsa verde', False)]),
    ('¿Por qué es peligroso romper un bombillo ahorrador?', 'Los bombillos fluorescentes tienen mercurio. Se entregan enteros en un punto posconsumo de bombillas.', 3,
     [('Porque tiene mercurio', True), ('Porque tiene plomo en el vidrio', False), ('No es peligroso', False)]),
    ('¿Cómo debes preparar una batería recargable de litio (power bank o celular) antes de llevarla al punto posconsumo?', 'Cubrir los polos con cinta aislante evita cortocircuitos o incendios durante el almacenamiento y transporte.', 3,
     [('Perforarla para que pierda carga', False), ('Cubrir sus polos con cinta aislante sin perforarla y entregarla en un punto posconsumo', True), ('Enjuagarla con agua y jabón', False)]),
    ('¿Qué se debe hacer con un envase vacío de insecticida o plaguicida doméstico?', 'Los envases de plaguicidas tienen residuos tóxicos: no los laves ni los perfores; entrégalos tapados en un punto posconsumo de plaguicidas.', 3,
     [('Lavarlo bien y ponerlo en la bolsa blanca', False), ('Entregarlo tapado, sin perforar ni lavar, en un punto posconsumo de plaguicidas', True), ('Perforarlo y botarlo en la bolsa negra', False)]),
    ('Si una caja de pizza tiene la base llena de grasa pero la tapa está completamente limpia, ¿cuál es la separación correcta?', 'El cartón limpio sí se aprovecha (bolsa blanca), mientras que la parte con grasa contamina el reciclaje y va en la bolsa negra.', 3,
     [('Toda la caja va en la bolsa blanca', False), ('Separar la tapa limpia para la bolsa blanca y poner la base con grasa en la bolsa negra', True), ('Toda la caja va en la bolsa verde', False)]),
    ('¿Dónde se deben entregar los medicamentos vencidos de uso veterinario (mascotas)?', 'Los medicamentos veterinarios también son residuos posconsumo: se entregan en su empaque en puntos autorizados de veterinarias o posconsumo.', 3,
     [('Por el desagüe con abundante agua', False), ('En su empaque original en un punto posconsumo de medicamentos veterinarios', True), ('En la bolsa negra junto a los residuos sanitarios', False)]),
]

PUNTOS_DEMO = [
    ('Punto posconsumo del centro comercial (ejemplo)', 'Dirección de ejemplo', 'Chapinero', 'Lunes a domingo, 10:00 a. m. a 8:00 p. m.',
     ['Pilas', 'Batería de celular', 'Bombillo ahorrador', 'Medicamentos vencidos']),
    ('Droguería con contenedor de medicamentos (ejemplo)', 'Dirección de ejemplo', 'Suba', 'Lunes a sábado, 8:00 a. m. a 9:00 p. m.',
     ['Medicamentos vencidos']),
    ('Punto ecológico del conjunto (ejemplo)', 'Dirección de ejemplo', 'Kennedy', 'Todos los días, 6:00 a. m. a 10:00 p. m.',
     ['Pilas', 'Aceite de cocina usado', 'Cargador y cables']),
    ('Jornada de recolección de electrónicos (ejemplo)', 'Dirección de ejemplo', 'Engativá', 'Último sábado de cada mes, 9:00 a. m. a 3:00 p. m.',
     ['Celular viejo', 'Computador', 'Cargador y cables', 'Pequeños electrodomésticos']),
]

# Residuos especiales adicionales que reciben los puntos posconsumo oficiales de Bogotá
RESIDUOS_POSCONSUMO_EXTRA = [
    ('Batería de carro o moto', 'batería de plomo, acumulador de carro, batería de moto', 'POSCONSUMO', 'pilas-y-baterias', 'no la abras ni la voltees: tiene ácido; entrégala en un taller o punto de baterías plomo-ácido'),
    ('Nevera, lavadora o estufa', 'nevera, lavadora, estufa, horno, electrodoméstico grande, línea blanca', 'POSCONSUMO', 'aparatos-electricos-y-electronicos', 'entrégala completa; pregunta antes si el punto recibe aparatos grandes'),
    ('Llantas', 'llanta, neumático, llanta de carro, llanta de bicicleta', 'POSCONSUMO', '', 'nunca la quemes ni la dejes en la calle; llévala a un punto de llantas'),
    ('Medicamentos veterinarios', 'medicamento de mascota, remedios del perro, medicamentos uso veterinario', 'POSCONSUMO', 'medicamentos-vencidos', 'déjalos en su empaque; llévalos a una veterinaria con contenedor posconsumo'),
    ('Envases de insecticidas y plaguicidas', 'insecticida, plaguicida, veneno para cucarachas, raid, fumigante', 'POSCONSUMO', '', 'no los perfores ni los laves; entrégalos tapados en un punto de plaguicidas'),
    ('CD y DVD', 'cd, dvd, disco compacto, empaques de cd', 'POSCONSUMO', 'aparatos-electricos-y-electronicos', 'entrégalos con o sin su caja'),
    ('Ropa y textiles', 'ropa, ropa vieja, textiles, zapatos, telas, ropa usada', 'POSCONSUMO', '', 'si está en buen estado dónala; si no, entrégala limpia y seca en un punto de moda circular'),
]

# Tipos de residuo del Visor Geográfico Ambiental de la SDA (api/v1/residuo) → residuos de EcoParce
SDA_A_ECOPARCE = {
    1: ['Aceite de cocina usado'],
    2: ['Batería de carro o moto'],
    3: ['Bombillo ahorrador'],
    4: ['Computador', 'Cargador y cables'],
    5: ['Celular viejo', 'Pequeños electrodomésticos', 'Cargador y cables', 'Computador'],
    6: ['Nevera, lavadora o estufa'],
    7: ['Llantas'],
    8: ['Medicamentos vencidos'],
    9: ['Medicamentos veterinarios'],
    10: ['Pilas', 'Batería de celular'],
    11: ['Envases de insecticidas y plaguicidas'],
    16: ['CD y DVD'],
    17: ['Ropa y textiles'],
}
