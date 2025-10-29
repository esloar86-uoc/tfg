# Taxonomía de Categorías · TFG Soporte Técnico

Definición de las 8 categorías de tickets de soporte.

| Código | Nombre                   | Descripción                                            | Incluye | Excluye |
|--------|--------------------------|--------------------------------------------------------|----------|----------|
| ACC    | Acceso / Autenticación   | Login, MFA, contraseñas, permisos, bloqueo de cuentas. | Active Directory, SSO, restablecer contraseña. | Correo (MAIL), Red (NET). |
| SW     | Software / Licencias     | Instalación, actualizaciones, errores.                 | Office, drivers, parches, bugs. | Aplicaciones de negocio (APP). |
| HW     | Hardware / Dispositivos  | Fallos físicos o periféricos.                          | Portátiles, monitores, impresoras, baterías. | Software corporativo. |
| NET    | Red / Conectividad       | Incidencias VPN, DNS, IP, proxy.                       | Wi-Fi, routers, latencia, desconexiones. | Outlook (MAIL). |
| MAIL   | Correo / Calendarios     | Buzones, Outlook, envío/recepción.                     | SMTP, IMAP, POP3, Exchange. | VPN/redes (NET). |
| APP    | Aplicaciones de Negocio  | Sistemas de gestión corporativos.                      | SAP, CRM, Dynamics, Jira, SharePoint, Power BI. | Software genérico o hardware. |
| SRV    | Solicitudes / Altas      | Peticiones estándar, procedimientos.                   | Crear usuario, cómo hacer, altas/bajas. | Incidencias técnicas. |
| POL    | Seguridad / Políticas    | Bloqueos, malware, cifrado, políticas.                 | Defender, antivirus, DLP, ransomware. | Hardware/software común. |

## Criterios de revisión manual
1. Leer `resumen`.
2. Corregir según dominio predominante.
3. En caso de duda:
   - Login/acceso -> ACC
   - SAP, Oracle, Power BI -> APP
   - Outlook -> MAIL
   - VPN/DNS -> NET
   - Dispositivo físico -> HW
   - Petición “cómo hacer” -> SRV
   - Defender/malware -> POL
   - Si nada aplica -> SW

