# Roadmap — Cocos Capital To Google Spreadsheet

> Última actualización: 2026-02-21

## ✅ Implementado

### Core
- **Login con 2FA** — Autenticación automática con extracción de código desde Gmail
- **Sync de operaciones** — Obtiene compras/ventas desde la API de Cocos Capital
- **Match de operaciones** — Algoritmo de matching exacto + acumulado + ventas acumuladas
- **Cálculo de rentabilidad** — Rentabilidad en % y ARS para posiciones cerradas
- **Precios en tiempo real** — Obtiene precio actual para operaciones abiertas (término 48hs)

### Google Sheets
- **Inserción de operaciones** — Formato template con columnas estandarizadas
- **Total diario** — Balance ARS + USD en pestaña separada
- **Filtro de duplicados** — Evita reinsertar operaciones ya guardadas

### Infraestructura
- **Soporte GCP** — Compatible con Google Cloud Functions (params event/context)
- **Dockerfile** — Contenedorización básica
- **Logging** — Logger configurado para debug

## 🚧 En progreso

*No hay desarrollo activo detectado.*

## 📋 Backlog

- [ ] Scheduler automático — Cron o Cloud Scheduler para sync periódico
- [ ] Alertas — Notificaciones cuando una operación supera X% de ganancia/pérdida
- [ ] Manejo de errores robusto — Retry en caso de fallo de API
- [ ] Tests unitarios — Cobertura para matching y transformaciones
- [ ] Soporte multi-cuenta — Varias cuentas de Cocos en un solo script

## 💡 Ideas

- Dashboard web con resumen de portfolio
- Integración con Telegram para alertas de precio
- Histórico de total diario con gráficos
- Comparación de rendimiento vs benchmark (Merval, S&P500 MEP)
- Export a otros formatos (CSV, JSON para análisis)

---
*Generado por Brújula 🧭*
