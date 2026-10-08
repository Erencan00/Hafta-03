/*********************************************************************
*                   (c) SEGGER Microcontroller GmbH                  *
*                        The Embedded Experts                        *
*                           www.segger.com                           *
**********************************************************************
*                                                                    *
*         SEGGER SystemView  * Real-time application analysis        *
*              https://github.com/SEGGERMicro/SystemView             *
*                                                                    *
**********************************************************************

---------------------------END-OF-HEADER------------------------------

Purpose : SEGGER SystemView configuration file.
          Set defines which deviate from the defaults (see SEGGER_SYSVIEW_ConfDefaults.h) here.          

Additional information:
  Required defines which must be set are:
    SEGGER_SYSVIEW_GET_TIMESTAMP
    SEGGER_SYSVIEW_GET_INTERRUPT_ID
  For known compilers and cores, these might be set to good defaults
  in SEGGER_SYSVIEW_ConfDefaults.h.
  
  SystemView needs a (nestable) locking mechanism.
  If not defined, the RTT locking mechanism is used,
  which then needs to be properly configured.
*/

#ifndef SEGGER_SYSVIEW_CONF_H
#define SEGGER_SYSVIEW_CONF_H

/*********************************************************************
*
*       Defines, configurable
*
**********************************************************************
*/

/*********************************************************************
*
*       Define: SEGGER_SYSVIEW_SECTION
*
*  Description
*    Section to place the SystemView RTT Buffer into.
*  Default
*    undefined: Do not place into a specific section.
*  Notes
*    If SEGGER_RTT_SECTION is defined, the default changes to use
*    this section for the SystemView RTT Buffer, too.
*/
#if !(defined SEGGER_SYSVIEW_SECTION) && (defined SEGGER_RTT_BUFFER_SECTION)
  #define SEGGER_SYSVIEW_SECTION                  SEGGER_RTT_BUFFER_SECTION
#endif


/*********************************************************************
* Hafta-01 ayarlari                                                  *
**********************************************************************
*/
/* Hedefteki olay tamponu. ST-Link koprusu (tools/sysview_stlink.py)
 * bu tamponu ~1 ms araliklarla okur; UART TX kesmeleri yogunken
 * tasmayi onlemek icin varsayilan 1 KB yerine 8 KB. */
#define SEGGER_SYSVIEW_RTT_BUFFER_SIZE          (8192)

/* Kimlikler (TCB/kuyruk adresleri) 0x20000000'dan itibaren 4'e bolunerek
 * kodlanir: olaylar kisalir. */
#define SEGGER_SYSVIEW_ID_BASE                  (0x20000000)
#define SEGGER_SYSVIEW_ID_SHIFT                 (2)


#endif  // SEGGER_SYSVIEW_CONF_H

/*************************** End of file ****************************/
