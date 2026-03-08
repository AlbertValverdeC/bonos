# Contenido anterior del repositorio

Este repositorio contenía anteriormente el proyecto **calculadora-bonos**, una aplicación de cálculo de bonificaciones basada en precios de compra negociados. A continuación se detalla lo que había:

---

## Estructura que existía

```
bonos/
├── formula.js            ← Lógica principal de cálculo de bonos
├── package.json          ← Proyecto Node.js "calculadora-bonos" v1.0.0
├── package-lock.json     ← Dependencias fijadas
├── firebase.json         ← Configuración de Firebase Hosting
├── .firebaserc           ← Proyecto Firebase: "calculadora-bonos"
├── .gitignore            ← Reglas de exclusión estándar de Node/Firebase
├── public/
│   └── index.html        ← Plantilla por defecto de Firebase Hosting
└── y/
    └── index.html        ← Copia de la plantilla de Firebase (prueba)
```

---

## Detalle de la lógica (`formula.js`)

El archivo principal implementaba un sistema de cálculo de bonificaciones con los siguientes pasos:

### 1. Precio base
- Recibía un `priceFisting` (precio en €/g)
- Fórmula: `basePrice = (priceFisting - 1) * 0.73 - 1.7`

### 2. Rangos dinámicos de compra
Usaba un factor de escala (`basePrice / 64`) para definir 4 rangos:

| Rango       | Límite inferior | Límite superior | Bono máximo    |
|-------------|-----------------|-----------------|----------------|
| Excelente   | 40 × factor     | 43 × factor     | 0.90 × factor  |
| Medio       | 43.1 × factor   | 49 × factor     | 0.70 × factor  |
| Bajo        | 49.1 × factor   | 53 × factor     | 0.40 × factor  |
| Consulta    | 53.1 × factor   | 62 × factor     | 0.10 × factor  |

Si el precio de compra superaba el rango "Consulta", el bono era 0 (negociación rota).

### 3. Interpolación lineal
Dentro de cada rango, el bono por gramo se interpolaba linealmente, decreciendo conforme subía el precio de compra.

### 4. Bono total
`totalBonus = bonusPerGram × quantity`

### Modo revisión
Con `review: true`, retornaba solo los rangos calculados sin necesitar precio de compra ni cantidad.

---

## Tecnologías que usaba
- **Node.js** con Express y PostgreSQL (`pg`)
- **Firebase Hosting** (SDK v11.3.1)
- **jsonwebtoken** para autenticación
- **winston** para logging

## Notas
- El formato de `formula.js` (con `$json` y `return [{json: {...}}]`) sugería que se ejecutaba dentro de **n8n** (plataforma de automatización).
- El `package.json` tenía ~470 dependencias directas (muchas transitivas incluidas por error).
- La interfaz web no estaba desarrollada (solo la plantilla por defecto de Firebase).

---

*Este archivo fue generado como registro histórico antes de reutilizar el repositorio para un nuevo proyecto.*
