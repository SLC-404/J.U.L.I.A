// Que datos necesita el asistente en las "Notas del caso" para cada
// servicio. Se muestran al crear o editar un caso, y con "Usar plantilla" se
// pegan como renglones para que la Lic. solo los llene. Entre mas completos,
// menos deja el asistente entre [corchetes] y menos inventa.

export type Guia = string[]

// Va al final de casi todos los juicios.
const JUICIO = [
  'Expediente y juzgado (si ya hay juicio)',
  'Contraparte: nombre completo y domicilio para emplazarla',
]
const CIERRE = [
  'Qué se quiere pedir al juez',
  'Documentos que tiene el cliente (actas, credencial, contratos…)',
]

const GUIAS: Record<string, Guia> = {
  'divorcio incausado': [
    ...JUICIO,
    'Fecha y lugar del matrimonio, número de acta y régimen (sociedad conyugal o separación de bienes)',
    'Último domicilio conyugal',
    'Hijos: nombre completo y edad de cada uno',
    'Desde cuándo están separados',
    'Propuesta de convenio: quién se queda con los hijos, convivencias, pensión, casa y bienes',
    ...CIERRE,
  ],
  'divorcio voluntario': [
    'Nombre completo y domicilio de los dos cónyuges',
    'Fecha y lugar del matrimonio, número de acta y régimen',
    'Hijos: nombre completo y edad',
    'Lo que ya acordaron: guarda y custodia, convivencias, pensión (monto y forma de pago), bienes',
    'Juzgado donde se va a presentar',
    'Documentos que tienen',
  ],
  'guarda y custodia y pension alimenticia': [
    ...JUICIO,
    'Hijos: nombre completo, edad y con quién viven ahora',
    'Por qué el cliente debe quedarse con los hijos (cuidados, escuela, salud)',
    'Ingresos o trabajo de quien debe pagar la pensión',
    'Gastos de los hijos (escuela, comida, salud) y monto de pensión que se pide',
    'Convivencias que se proponen para el otro padre',
    ...CIERRE,
  ],
  'pension alimenticia': [
    ...JUICIO,
    'Quién recibe la pensión (hijos o cónyuge): nombre y edad',
    'Trabajo e ingresos de quien debe pagar (empresa, sueldo aproximado)',
    'Gastos mensuales y monto que se pide',
    'Si ya hay pensión fijada: cuánto, desde cuándo y si dejó de pagar',
    ...CIERRE,
  ],
  'perdida de la patria potestad': [
    ...JUICIO,
    'Hijos: nombre completo y edad',
    'Causa: abandono, falta de pago de alimentos, violencia… con fechas',
    'Desde cuándo no convive ni paga',
    'Testigos o pruebas que hay',
    ...CIERRE,
  ],
  'controversia del orden familiar': [
    ...JUICIO,
    'Cuál es el problema familiar (convivencias, alimentos, violencia…)',
    'Personas involucradas y su parentesco',
    'Fechas de lo que pasó',
    ...CIERRE,
  ],
  'liquidacion de sociedad conyugal': [
    'Expediente del divorcio y juzgado',
    'Fecha de la sentencia de divorcio',
    'Bienes de la sociedad: casa, terrenos, vehículos, cuentas (con datos)',
    'Deudas comunes',
    'Cómo se propone repartirlos',
    'Documentos que tiene (escrituras, facturas)',
  ],
  'juicio sucesorio intestamentario': [
    'Expediente y juzgado (si ya hay juicio)',
    'Nombre completo de quien falleció y fecha de defunción',
    'Quién denunció la sucesión (si no fue el cliente)',
    'Parentesco del cliente con quien falleció',
    'Otros herederos: nombre y parentesco',
    'Bienes que dejó (casa, terreno, cuentas)',
    'Cuándo notificaron al cliente y qué le pidieron (si aplica)',
    'Qué quiere pedir: reconocerse heredero, proponer albacea, oponerse…',
    'Documentos: acta de defunción, actas de nacimiento o matrimonio que prueban el parentesco',
  ],
  'informacion ad perpetuam (concubinato)': [
    'Nombre completo de la pareja (y si falleció, fecha de defunción)',
    'Desde cuándo vivieron juntos y en qué domicilio',
    'Hijos en común: nombre y edad',
    'Para qué se necesita acreditar el concubinato (pensión, herencia, IMSS…)',
    'Testigos: nombre y domicilio',
    'Documentos que tiene',
  ],
  'rectificacion de acta': [
    'Qué acta es (nacimiento, matrimonio, defunción), número, libro y oficialía del Registro Civil',
    'Dato equivocado tal como aparece en el acta',
    'Cómo debe decir correctamente',
    'Por qué se necesita corregir y con qué documentos se prueba el dato correcto (CURP, INE, actas de los hijos…)',
    'Juzgado donde se va a presentar',
  ],
  'nulidad y cancelacion de acta': [
    'Qué acta se quiere anular: número, libro y oficialía',
    'Por qué es nula (registro doble, datos falsos…)',
    'Qué acta debe quedar vigente',
    'Documentos que lo prueban',
    'Juzgado donde se va a presentar',
  ],
  'plenario de posesion': [
    ...JUICIO,
    'Ubicación, medidas y colindancias del inmueble',
    'Cómo adquirió el cliente la posesión (contrato, herencia…) y desde cuándo',
    'Cómo y cuándo le quitaron o perturbaron la posesión',
    'Testigos y documentos (contrato, recibos de predial, fotos)',
    'Qué se quiere pedir al juez',
  ],
  'juicio ordinario civil': [
    ...JUICIO,
    'Qué se reclama y por qué (hechos con fechas)',
    'Montos o bienes en disputa',
    ...CIERRE,
  ],
  'medios preparatorios a juicio': [
    'Contra quién y para qué juicio futuro se preparan',
    'Qué se necesita: confesión, exhibición de documentos, inspección…',
    'Preguntas o documentos que se quieren obtener',
    'Juzgado donde se va a presentar',
  ],
  'juicio ejecutivo mercantil': [
    ...JUICIO,
    'Documento base: pagaré o letra (fecha, monto, vencimiento, quién lo firmó)',
    'Si es endoso en procuración: nombre del acreedor original',
    'Cuánto se debe, abonos e intereses pactados',
    'Bienes del deudor que se pueden embargar',
    'Qué se quiere pedir al juez',
  ],
  'juicio ordinario mercantil': [
    ...JUICIO,
    'Contrato o relación comercial y qué se incumplió',
    'Montos reclamados',
    ...CIERRE,
  ],
  'contrato de compraventa': [
    'Vendedor y comprador: nombre completo, domicilio y identificación',
    'Inmueble: ubicación, medidas, colindancias y superficie',
    'Cómo adquirió el vendedor (escritura, contrato anterior, herencia)',
    'Precio, forma de pago y fechas',
    'Fecha y lugar de firma, testigos',
  ],
  'contrato de promesa de venta': [
    'Promitente vendedor y comprador: nombre completo y domicilio',
    'Inmueble: ubicación, medidas y colindancias',
    'Precio, anticipo y cómo se pagará el resto',
    'Plazo para firmar el contrato definitivo',
    'Penas si alguien no cumple',
  ],
  'contrato de donacion': [
    'Donante y donatario: nombre completo, domicilio y parentesco',
    'Bien que se dona: ubicación, medidas y colindancias',
    'Cómo lo adquirió el donante',
    'Fecha y lugar de firma, testigos',
  ],
  'contrato de arrendamiento': [
    'Arrendador y arrendatario: nombre completo y domicilio',
    'Inmueble que se renta y para qué uso (casa, local)',
    'Renta mensual, día de pago y depósito',
    'Plazo (desde cuándo y hasta cuándo)',
    'Fiador (si hay) y condiciones especiales',
  ],
  'contrato de permuta': [
    'Las dos partes: nombre completo y domicilio',
    'Bien que entrega cada parte: ubicación, medidas y colindancias',
    'Diferencia en dinero (si hay)',
    'Fecha y lugar de firma',
  ],
  'contrato de mandato': [
    'Mandante y mandatario: nombre completo y domicilio',
    'Para qué asuntos o trámites es el mandato',
    'Si es general o especial, y vigencia',
  ],
  convenio: [
    'Partes: nombre completo y domicilio',
    'Qué se está arreglando y los antecedentes',
    'Cada compromiso: quién, qué, cuánto y cuándo',
    'Qué pasa si alguien no cumple',
  ],
  'denuncia penal': [
    'Delito y lugar donde pasó',
    'Fecha y hora de los hechos',
    'Qué pasó, paso a paso',
    'Probable responsable: nombre o media filiación',
    'Testigos y pruebas (fotos, facturas, mensajes)',
    'Daños o pérdidas y su valor',
  ],
  'defensa penal': [
    'Número de causa o carpeta y juzgado (control, oral o ejecución)',
    'Delito que se le imputa al cliente',
    'Etapa del proceso y próxima audiencia',
    'Qué se quiere pedir (copias, nombrar abogado, beneficio, apelación…)',
  ],
  'juicio de amparo': [
    'Acto que se reclama y autoridad que lo emitió',
    'Fecha en que se notificó o conoció el acto',
    'Expediente de origen',
    'Derechos que se violan y por qué',
    'Si se pide suspensión',
  ],
  'copias certificadas y tramites de expediente': [
    'Expediente y juzgado',
    'Juicio y partes',
    'Qué copias o trámite se necesita y para qué',
  ],
  'oficios y gestiones administrativas': [
    'Dependencia o persona a quien va dirigido (nombre y cargo)',
    'Qué se solicita y para qué',
    'Antecedentes y fechas',
    'Documentos que se anexan',
  ],
}

const GENERICA: Guia = [
  'Expediente y juzgado (si hay juicio)',
  'Partes: nombre completo y papel de cada una',
  'Qué pasó (hechos con fechas)',
  ...CIERRE,
]

function clave(nombre: string) {
  return nombre
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

export function guiaDelServicio(nombreServicio?: string | null): Guia {
  if (!nombreServicio) return GENERICA
  return GUIAS[clave(nombreServicio)] ?? GENERICA
}

/** Renglones "Dato: " para pegar en las notas y llenarlos. */
export function plantillaDeNotas(guia: Guia) {
  // "Qué quiere pedir: reconocerse heredero…" -> "Qué quiere pedir: "
  // "Bienes que dejó (casa, terreno)"         -> "Bienes que dejó: "
  return guia
    .map((g) => `${g.split(':')[0].replace(/\s*\(.*?\)\s*$/, '').trim()}: `)
    .join('\n')
}
