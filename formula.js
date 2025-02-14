// --- 1. Cálculo del nuevo precio base (lo que "te pagan") ---
const fisting = $json.priceFisting; // Ejemplo: 80 €/g
console.log("fisting:", fisting);

const reviewMode = $json.review === true;  // Modo revisión
console.log("Modo revisión:", reviewMode);

const adjustedFisting = fisting - 1;  
console.log("adjustedFisting:", adjustedFisting);

const multiplied = adjustedFisting * 0.73;
console.log("multiplied:", multiplied);

const basePrice = multiplied - 1.7;  
console.log("basePrice:", basePrice);

// --- 2. Cálculo de los rangos de compra ---
// Se utiliza el factor para escalar, basándonos en un sistema original de 64 €/g.
const factor = basePrice / 64;  
console.log("factor:", factor);

const excellentLower = 40 * factor;  // Ej.: 40 * factor
const excellentUpper = 43 * factor;  // Ej.: 43 * factor
const mediumLower   = 43.1 * factor;   // Ej.: 43.1 * factor
const mediumUpper   = 49 * factor;     // Ej.: 49 * factor
const lowLower      = 49.1 * factor;    // Ej.: 49.1 * factor
const lowUpper      = 53 * factor;      // Ej.: 53 * factor
const consultLower  = 53.1 * factor;    // Ej.: 53.1 * factor
const consultUpper  = 62 * factor;      // Ej.: 62 * factor

console.log("Rangos:", {
  excelente: { lower: excellentLower, upper: excellentUpper },
  medio: { lower: mediumLower, upper: mediumUpper },
  bajo: { lower: lowLower, upper: lowUpper },
  consulta: { lower: consultLower, upper: consultUpper }
});

// Si estamos en modo revisión, retornamos únicamente los datos de rangos.
if (reviewMode) {
  console.log("Modo revisión activado, retornando solo rangos.");
  return [{
    json: {
      priceFisting: fisting,
      adjustedFisting: adjustedFisting,
      basePrice: basePrice,
      factor: factor,
      rangos: {
        excelente: { lower: excellentLower, upper: excellentUpper },
        medio: { lower: mediumLower, upper: mediumUpper },
        bajo: { lower: lowLower, upper: lowUpper },
        consulta: { lower: consultLower, upper: consultUpper }
      },
      note: "Datos de rangos basados en el precio de fisting actual."
    }
  }];
}

// --- 3. Modo normal: se requieren purchasePrice y quantity ---
const purchasePrice = $json.purchasePrice; // Precio real de compra (€/g)
const quantity = $json.quantity;           // Cantidad en gramos

if (typeof purchasePrice !== 'number' || typeof quantity !== 'number') {
  throw new Error("Debes introducir 'purchasePrice' y 'quantity' como números.");
}

console.log("purchasePrice:", purchasePrice, "quantity:", quantity);

let bonusPerGram;
let rangeLabel = "";

if (purchasePrice <= excellentUpper) {
  const slope = ((0.70 * factor) - (0.90 * factor)) / (excellentUpper - excellentLower);
  bonusPerGram = (0.90 * factor) + slope * (purchasePrice - excellentLower);
  rangeLabel = "Excelente";
} else if (purchasePrice <= mediumUpper) {
  const slope = ((0.40 * factor) - (0.70 * factor)) / (mediumUpper - mediumLower);
  bonusPerGram = (0.70 * factor) + slope * (purchasePrice - mediumLower);
  rangeLabel = "Medio";
} else if (purchasePrice <= lowUpper) {
  const slope = ((0.10 * factor) - (0.40 * factor)) / (lowUpper - lowLower);
  bonusPerGram = (0.40 * factor) + slope * (purchasePrice - lowLower);
  rangeLabel = "Bajo";
} else if (purchasePrice <= consultUpper) {
  const slope = (0 - (0.10 * factor)) / (consultUpper - consultLower);
  bonusPerGram = (0.10 * factor) + slope * (purchasePrice - consultLower);
  rangeLabel = "Consulta";
} else {
  bonusPerGram = 0;
  rangeLabel = "Negociación rota (sin bono)";
}

const totalBonus = bonusPerGram * quantity;
console.log("bonusPerGram:", bonusPerGram, "totalBonus:", totalBonus, "rangeLabel:", rangeLabel);

// --- 4. Preparar y retornar la salida ---
return [{
  json: {
    priceFisting: fisting,
    adjustedFisting: adjustedFisting,
    basePrice: basePrice,
    factor: factor,
    rangos: {
      excelente: { lower: excellentLower, upper: excellentUpper },
      medio: { lower: mediumLower, upper: mediumUpper },
      bajo: { lower: lowLower, upper: lowUpper },
      consulta: { lower: consultLower, upper: consultUpper }
    },
    purchasePrice: purchasePrice,
    quantity: quantity,
    bonusPerGram: bonusPerGram,
    totalBonus: totalBonus,
    range: rangeLabel,
    note: "Si el precio de compra > " + consultUpper.toFixed(2) + " €/g, se rompe la negociación."
  }
}];
