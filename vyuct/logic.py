"""Rozhodovacia logika — čo a kedy poslať."""
import logging

log = logging.getLogger('vyuctovanie')


def decide(msgs, now_local, force_info=False):
    """Z obohatených správ rozhodne, čo poslať.

    Vráti zoznam akcií: [('settlement', total_h, od, do, items)] alebo
    [('info', total_h, items)]. items = [(dátum, autor, hodiny, popis), ...].
    """
    uzs = [m for m in msgs if m['uz']]
    last_uz = uzs[-1] if uzs else None

    # 1) Uzávierka bez vyúčtovania za ňou → pošli vyúčtovanie hneď.
    #    Okno sa kotví na POSLEDNÉ poslané vyúčtovanie, nie na predošlú
    #    uzávierku — dve uzávierky tesne po sebe tak nezhltnú hodiny
    #    nazbierané pred prvou z nich.
    if last_uz and not any(m['settlement'] and m['id'] > last_uz['id'] for m in msgs):
        start_id = max((m['id'] for m in msgs if m['settlement']), default=0)
        period = [m for m in msgs if start_id < m['id'] < last_uz['id']]
        total = sum(m['hours'] for m in period)
        od = period[0]['date'] if period else last_uz['date']
        items = [(m['date'], m['author'], h, d)
                 for m in period for h, d in m['entries']]
        return [('settlement', total, od, last_uz['date'], items)]

    # 2) Večerné priebežné info — max 1× denne, len ak pribudli nové hodiny.
    period_start = last_uz['id'] if last_uz else 0
    period = [m for m in msgs if m['id'] > period_start]
    total = sum(m['hours'] for m in period)
    items = [(m['date'], m['author'], h, d)
             for m in period for h, d in m['entries']]

    if force_info:
        if total > 0:
            return [('info', total, items)]
        log.info('force-info: žiadne hodiny od poslednej uzávierky — nič na poslanie.')
        return []

    # Len o 20:00 (okno 20:00–20:59) — tolerancia na 10-min takt timera a krátky
    # výpadok behu presne o 20:00. Hodiny zapísané po 20:59 idú do infa až
    # nasledujúci deň o 20:00. (Vlastnícke rozhodnutie 2026-08-20, ticket #4.)
    in_window = now_local.hour == 20
    already_today = any(m['info'] and m['date'].date() == now_local.date() for m in msgs)
    bot_ids = [m['id'] for m in msgs if m['is_bot']]
    baseline = max(bot_ids + [period_start])
    new_hours = any(m['hours'] > 0 and m['id'] > baseline for m in msgs)

    if in_window and not already_today and new_hours and total > 0:
        return [('info', total, items)]
    log.info('info sa neposiela: večerné okno=%s, dnes už bolo=%s, nové hodiny=%s, súčet=%s h',
             in_window, already_today, new_hours, total)
    return []
