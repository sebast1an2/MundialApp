# 🎨 Análisis Lógico del Flujo de Plantillas (Frontend)

La interfaz de **MundialApp** funciona mediante un sistema de plantillas Jinja2 (`app/templates/public/`) que reaccionan dinámicamente a la configuración del evento. A continuación, se detalla el flujo completo del participante y cómo las **nuevas opciones implementadas** cobran vida en la vista sin modificar el código base.

---

## 1. El Flujo del Participante

### A. Selección del Evento (`home.html`)
El usuario llega al inicio y visualiza los eventos activos. 
- **Novedad visual:** Se implementó una sección destacada (`troquel-banner`) que anuncia la alianza institucional con *Troquel Grafic*, utilizando un diseño moderno con gradientes y medallas de confianza.

### B. El Gatekeeper y Modal de Reglas (`validate.html`)
Cuando el usuario intenta participar por primera vez (ingresar su cédula), el sistema lo redirige a esta plantilla. Aquí es donde la mayoría de las **nuevas opciones configurables** entran en acción.
Se despliega un gran modal interactivo (`infoModal`) que obliga al usuario a leer las reglas y la información financiera antes de poder escribir su cédula:

1. **Premios (`prize_first`, `prize_second`, `prize_third`):** Si el administrador configuró premios, la plantilla suma estos valores (`total_prize`) y muestra un bloque destacado ("Valor total del premio"). Además, genera tarjetas individuales (Oro, Plata, Bronce) con los montos exactos de cada lugar.
2. **Costo de Participación (`participation_fee`):** Se muestra en una etiqueta (`payment-fee-badge`) indicando el valor de la inscripción.
3. **Medio de Pago (`nequi_number`):** Si está configurado, aparece un bloque visual verde (estilo Nequi) con el número y una instrucción directa de enviar el comprobante por WhatsApp a ese mismo número.
4. **Scroll-gate:** Mediante JavaScript embebido, el botón de "¡Participar!" está oculto. El usuario **debe** hacer scroll hasta el final del texto legal/informativo para que el botón se revele, asegurando que leyó las condiciones.

### C. Dashboard del Evento (`event.html`)
Una vez validada la cédula, el participante entra al panel principal del evento.
- **Progreso del Torneo:** Una barra visual (`phase-stepper`) muestra las fases cerradas y la fase activa.
- **Botón Flotante (FAB):** Si hay una fase abierta y el usuario no ha predicho, un botón flotante llamativo y animado (`fab-predict`) le incita a "Hacer Predicción".
- **Partidos del Día:** Un listado en tiempo real de los partidos programados para la fecha actual. Dependiendo del estado del partido (en juego, finalizado, próximo), cambian los colores y etiquetas.

### D. Formulario de Predicciones (`predictions_form.html`)
El usuario llena sus resultados. 
- **Lógica reactiva (JS):** Si el evento está en una fase eliminatoria y el usuario digita un empate (ej. 1 - 1), el JavaScript embebido detecta la igualdad y **despliega dinámicamente un selector de penales** (`penalty-pred-section`) obligando al usuario a elegir qué equipo avanzará.

---

## 2. La Lógica de Privacidad y Ranking (`can_view_others_predictions`)

Una de las opciones más críticas implementadas recientemente es el booleano `can_view_others_predictions` configurado desde el panel admin. La lógica de las plantillas evalúa esta variable constantemente para ocultar o mostrar información estratégica:

* **En el Dashboard (`event.html`):** 
  * Si es `False`, el "Mini Ranking" lateral desaparece completamente.
  * Los botones de acceso directo a "Aciertos" o "Ver Pronósticos" de otros usuarios en los partidos del día se ocultan.
* **En el Menú Flotante Inferior (`base.html`):**
  * El enlace directo a "Ranking General" se condiciona (dependiendo de la fase o configuración, se restringe).
* **En el Ranking Principal (`ranking.html`):**
  * Si la privacidad está activada, los botones de "Comparar" (que permiten ver un cara-a-cara de los resultados del usuario vs un rival) no se renderizan en la tabla.

---

## 3. Resumen de Variables Inyectadas en Plantillas

| Opción de Base de Datos | Archivo Jinja afectado | Comportamiento Visual |
|---|---|---|
| `event.prize_first` | `validate.html` | Renderiza la tarjeta 🥇 y suma al "Total de Premios". |
| `event.participation_fee` | `validate.html` | Muestra la etiqueta morada de "Valor de participación". |
| `event.nequi_number` | `validate.html` | Genera la caja de instrucciones de transferencia vía WhatsApp. |
| `event.can_view_others_predictions` | `event.html`, `ranking.html` | Bloquea el renderizado de enlaces "Ver Aciertos" y el botón "Comparar". |
| `phase.is_prediction_open` | `event.html`, `participate.html` | Habilita/Deshabilita el Botón Flotante Animado (FAB). |

### Conclusión
Las plantillas están diseñadas con un alto nivel de condicionales lógicos (`{% if ... %}`). Esto permite que **MundialApp mute su comportamiento y reglas de negocio dinámicamente** con solo cambiar un switch o un número en el panel de administrador, sin necesidad de tocar una sola línea de código en producción.
