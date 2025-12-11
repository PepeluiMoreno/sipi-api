# 🏘️ Sistema Híbrido de Geografía con Entidades Menores

## 📋 Resumen

Sistema completo de geografía administrativa española con soporte para entidades de ámbito territorial inferior al municipio (parroquias, concejos, pedanías, etc.)

---

## 🗂️ Estructura de Datos

### Jerarquía Territorial

```
España
├── ComunidadAutonoma (19 + Ceuta + Melilla = 21)
│   └── Provincia (52)
│       └── Municipio (8.131)
│           └── EntidadMenor (~100.000 según Nomenclátor INE)
│               ├── Parroquia (Galicia: ~3.700)
│               ├── Concejo (Asturias: ~857)
│               ├── Pedanía (Murcia, Aragón)
│               ├── Entidad Local Menor (con personalidad jurídica)
│               ├── Núcleo de población
│               ├── Entidad singular
│               ├── Barrio
│               └── Otros...
```

---
