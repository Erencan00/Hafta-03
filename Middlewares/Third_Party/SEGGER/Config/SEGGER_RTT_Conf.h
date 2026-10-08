/*********************************************************************
*                   (c) SEGGER Microcontroller GmbH                  *
*                        The Embedded Experts                        *
*                           www.segger.com                           *
**********************************************************************
*                                                                    *
*        SEGGER RTT * Real Time Transfer for embedded targets        *
*                  https://github.com/SEGGERMicro/RTT                *
*                                                                    *
**********************************************************************

---------------------------END-OF-HEADER------------------------------
Purpose : User configuration file for RTT.
          For available configuration,
          refer to SEGGER_RTT_ConfDefaults.h.

----------------------------------------------------------------------
*/

#ifndef SEGGER_RTT_CONF_H
#define SEGGER_RTT_CONF_H

/* Hafta-01: kanal 0 (terminal) kullanilmiyor; RAM'den tasarruf.
 * SystemView kendi kanalini (SEGGER_SYSVIEW_RTT_BUFFER_SIZE) ayri ayirir. */
#define BUFFER_SIZE_UP                            (256)
#define BUFFER_SIZE_DOWN                          (16)

/* SEGGER_RTT_LOCK: BASEPRI = 0x20 -> oncelik 2..15 maskelenir. Izlenen tum
 * kesmeler (EXTI15_10, USART2, TIM3, SysTick) oncelik 5..15'te, yani RTT
 * yazimini bolemezler. Oncelik 0..1 kesmelerden SystemView API'si CAGRILMAMALI. */
#define SEGGER_RTT_MAX_INTERRUPT_PRIORITY         (0x20)

/* SEGGER_RTT_ASM_ARMv7M.S derlemeye eklenmedi: saf C yazim yolu kullanilir. */
#define RTT_USE_ASM                               (0)


/*********************************************************************
*
*       Defines, configurable
*
**********************************************************************
*/

#endif
/*************************** End of file ****************************/
