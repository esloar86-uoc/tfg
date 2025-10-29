# TFG — Optimización de la gestión de tickets en Jira (BI + Clasificación)

Estructura del repositorio y normas básicas para trabajo con **Git** en este proyecto.

## Estructura
(Ver árbol de carpetas en el zip - PDTE)

## Flujo de trabajo con ramas
- `main` (estable)
- Ramas de trabajo: `feat/...`, `fix/...`, `pec/...`

## Commits
- Mensajes breves: `ETL: normaliza prioridades y fechas a UTC`
- Commits pequeños y lógicos

## LFS
Git LFS (Large File Storage) se usa para binarios pesados.
Recomendado para `*.pbix` e imágenes grandes.

## Reproducibilidad
Guía de pasos para clonar, configurar el entorno y ejecutar el proyecto: **[runbook.md](./runbook.md)**.

## Datos / licencias
Este repositorio incluye datos de terceros:
- Kaggle 1: *dataset_kaggle_english__synthetic-it-call-center-tickets.csv*, CC0 (Public Domain). Fuente: <https://www.kaggle.com/datasets/kameronbrooks/synthetic-it-call-center-tickets-v1>.
- Kaggle 2: *dataset_kaggle_english_2__customer_support_tickets.csv*, CC BY 4.0. Fuente: <https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset>.