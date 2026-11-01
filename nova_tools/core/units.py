"""Birim dönüştürücü. Her kategori için temel birime göre katsayılar."""
from __future__ import annotations

# Her birim: (görünen ad, temel birime çarpan)
UNITS: dict[str, dict[str, float]] = {
    "Uzunluk": {
        "Milimetre (mm)": 0.001, "Santimetre (cm)": 0.01, "Metre (m)": 1.0,
        "Kilometre (km)": 1000.0, "İnç (in)": 0.0254, "Fit (ft)": 0.3048,
        "Yarda (yd)": 0.9144, "Mil (mi)": 1609.344, "Deniz mili (nmi)": 1852.0,
    },
    "Ağırlık": {
        "Miligram (mg)": 1e-6, "Gram (g)": 0.001, "Kilogram (kg)": 1.0, "Ton (t)": 1000.0,
        "Ons (oz)": 0.028349523125, "Pound (lb)": 0.45359237,
    },
    "Alan": {
        "Metrekare (m²)": 1.0, "Santimetrekare (cm²)": 1e-4, "Kilometrekare (km²)": 1e6,
        "Hektar (ha)": 1e4, "Dönüm": 1000.0, "Fitkare (ft²)": 0.09290304, "Akre (ac)": 4046.8564224,
    },
    "Hacim": {
        "Mililitre (ml)": 0.001, "Litre (l)": 1.0, "Metreküp (m³)": 1000.0,
        "Galon (ABD)": 3.785411784, "Galon (İng.)": 4.54609, "Bardak (ABD)": 0.2365882365,
        "Yemek kaşığı": 0.01478676478125, "Çay kaşığı": 0.00492892159375,
    },
    "Hız": {
        "m/s": 1.0, "km/sa": 1 / 3.6, "mil/sa": 0.44704, "Knot": 1852 / 3600, "ft/s": 0.3048,
    },
    "Zaman": {
        "Milisaniye": 0.001, "Saniye": 1.0, "Dakika": 60.0, "Saat": 3600.0,
        "Gün": 86400.0, "Hafta": 604800.0, "Yıl (365 gün)": 31536000.0,
    },
    "Veri": {
        "Bit": 0.125, "Bayt (B)": 1.0, "Kilobayt (KB)": 1024.0, "Megabayt (MB)": 1024.0 ** 2,
        "Gigabayt (GB)": 1024.0 ** 3, "Terabayt (TB)": 1024.0 ** 4,
        "Kilobayt (kB, SI)": 1000.0, "Megabayt (MB, SI)": 1e6, "Gigabayt (GB, SI)": 1e9,
    },
    "Basınç": {
        "Pascal (Pa)": 1.0, "Kilopascal (kPa)": 1000.0, "Bar": 1e5, "Atmosfer (atm)": 101325.0,
        "PSI": 6894.757293168, "mmHg": 133.322387415,
    },
    "Enerji": {
        "Joule (J)": 1.0, "Kilojoule (kJ)": 1000.0, "Kalori (cal)": 4.184,
        "Kilokalori (kcal)": 4184.0, "Watt-saat (Wh)": 3600.0, "Kilowatt-saat (kWh)": 3.6e6,
    },
    "Sıcaklık": {"Santigrat (°C)": 0, "Fahrenhayt (°F)": 0, "Kelvin (K)": 0},
}

CATEGORIES = list(UNITS.keys())


def _to_celsius(value: float, unit: str) -> float:
    if unit.startswith("Santigrat"):
        return value
    if unit.startswith("Fahrenhayt"):
        return (value - 32) * 5 / 9
    if unit.startswith("Kelvin"):
        return value - 273.15
    raise ValueError(f"Bilinmeyen sıcaklık birimi: {unit}")


def _from_celsius(value: float, unit: str) -> float:
    if unit.startswith("Santigrat"):
        return value
    if unit.startswith("Fahrenhayt"):
        return value * 9 / 5 + 32
    if unit.startswith("Kelvin"):
        return value + 273.15
    raise ValueError(f"Bilinmeyen sıcaklık birimi: {unit}")


def convert(category: str, value: float, from_unit: str, to_unit: str) -> float:
    if category not in UNITS:
        raise ValueError(f"Bilinmeyen kategori: {category}")
    table = UNITS[category]
    if from_unit not in table or to_unit not in table:
        raise ValueError("Bilinmeyen birim.")
    if category == "Sıcaklık":
        c = _to_celsius(value, from_unit)
        if c < -273.15 - 1e-9:
            raise ValueError("Mutlak sıfırın altında sıcaklık olamaz.")
        return _from_celsius(c, to_unit)
    return value * table[from_unit] / table[to_unit]
