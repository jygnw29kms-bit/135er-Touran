from pathlib import Path
import io, os, textwrap
import requests
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle,
    KeepTogether, Flowable
)

OUT = Path('dist/Touran_1T3_ESP32_CAN_Einbauanleitung_Originalbilder.pdf')
ASSET = Path('dist/install-guide-assets')
ASSET.mkdir(parents=True, exist_ok=True)
OUT.parent.mkdir(parents=True, exist_ok=True)

SOURCES = [
    ('j533_vw.png', 'https://www.vwtourande.com/images/books/475/13/N97-10001.png', 'VW Reparaturgrafik: Diagnose-Interface J533'),
    ('j533_trim.jpg', 'https://img.motor-talk.de/media/forum-beitraege/bilder/adresse-19-gateway-diagnoseinterface-t2614985/23757181/0_medium.jpg', 'Motor-Talk: Zugang Fahrerfussraum / Verkleidung'),
    ('rns_overview.png', 'https://www.vwtourande.com/images/books/475/7/N91-10927.png', 'VW Reparaturgrafik: RNS510 Steckverbinderuebersicht'),
    ('rns_can.png', 'https://www.vwtourande.com/images/books/475/8/N91-10928.png', 'VW Reparaturgrafik: 8-poliger Spannungs-/CAN-Stecker'),
    ('rns_pinout.jpg', 'https://a1.drive-data.ru/54e4b06s-960.jpg', 'RNS510/RCD510 Pinbelegung - Bild aus Einbaubeitrag'),
    ('waveshare.jpg', 'https://raw.githubusercontent.com/waveshareteam/ESP32-S3-CAN-2CH/main/assets/ESP32-S3-CAN-2CH.jpg', 'Waveshare ESP32-S3-CAN-2CH Produktfoto'),
    ('waveshare_docs.webp', 'https://docs.waveshare.net/assets/images/ESP32-S3-CAN-2CH-1-eb25a1c600d58b45ade39feda4f0dbe0.webp', 'Waveshare Dokumentation: Gehaeuse / Anschluesse'),
]

session = requests.Session()
session.headers.update({'User-Agent':'Mozilla/5.0 Touran-private-install-guide/1.0'})
failed = []
for fn, url, label in SOURCES:
    p = ASSET / fn
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        p.write_bytes(r.content)
        with PILImage.open(p) as im:
            im.verify()
    except Exception as e:
        failed.append((label, url, str(e)))
        if p.exists(): p.unlink()

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Title2', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=colors.HexColor('#20252B'), alignment=TA_CENTER, spaceAfter=8))
styles.add(ParagraphStyle(name='H1x', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, leading=19, textColor=colors.HexColor('#1B4F72'), spaceBefore=3, spaceAfter=7))
styles.add(ParagraphStyle(name='H2x', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12.5, leading=15, textColor=colors.HexColor('#333333'), spaceBefore=7, spaceAfter=4))
styles.add(ParagraphStyle(name='Bodyx', parent=styles['BodyText'], fontName='Helvetica', fontSize=9.3, leading=12.4, spaceAfter=5))
styles.add(ParagraphStyle(name='Small', parent=styles['BodyText'], fontName='Helvetica', fontSize=7.5, leading=9.2, textColor=colors.HexColor('#555555'), spaceAfter=4))
styles.add(ParagraphStyle(name='Warn', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=9.3, leading=12.2, textColor=colors.HexColor('#8B1A1A'), backColor=colors.HexColor('#FFF1E8'), borderColor=colors.HexColor('#D97706'), borderWidth=.6, borderPadding=6, spaceBefore=5, spaceAfter=7))
styles.add(ParagraphStyle(name='Ok', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=9.3, leading=12.2, textColor=colors.HexColor('#155724'), backColor=colors.HexColor('#EDF8EF'), borderColor=colors.HexColor('#6AA96B'), borderWidth=.6, borderPadding=6, spaceBefore=5, spaceAfter=7))

class Wiring(Flowable):
    def __init__(self, w=170*mm, h=50*mm):
        Flowable.__init__(self); self.width=w; self.height=h
    def draw(self):
        c=self.canv; w=self.width; h=self.height
        boxes=[(5,'J533 / T20'),(61,'ESP32-S3\nCAN-2CH-U'),(119,'Quadlock / Radio')]
        for x,t in boxes:
            c.setStrokeColor(colors.HexColor('#4C5967')); c.setFillColor(colors.HexColor('#F4F7FA'))
            c.roundRect(x*mm,15*mm,45*mm,24*mm,3*mm,fill=1,stroke=1)
            c.setFillColor(colors.black); c.setFont('Helvetica-Bold',9)
            lines=t.split('\n')
            for i,line in enumerate(lines): c.drawCentredString((x+22.5)*mm,(30-i*5)*mm,line)
        c.setStrokeColor(colors.HexColor('#A85418')); c.setLineWidth(2)
        c.line(50*mm,30*mm,61*mm,30*mm); c.line(106*mm,30*mm,119*mm,30*mm)
        c.setFont('Helvetica',7.5); c.setFillColor(colors.HexColor('#A85418'))
        c.drawCentredString(55.5*mm,34*mm,'CAN1 500 kbit/s')
        c.drawCentredString(112.5*mm,34*mm,'CAN2 100 kbit/s')
        c.setStrokeColor(colors.HexColor('#235D9F')); c.line(83*mm,15*mm,83*mm,5*mm)
        c.setFillColor(colors.HexColor('#235D9F')); c.drawCentredString(83*mm,1*mm,'USB zum Erisin')

def img(path, maxw=175*mm, maxh=112*mm):
    p=Path(path)
    if not p.exists(): return None
    with PILImage.open(p) as im:
        iw,ih=im.size
    scale=min(maxw/iw,maxh/ih)
    return Image(str(p),width=iw*scale,height=ih*scale)

def source_block(filename, label, source_url, maxh=105*mm):
    p=ASSET/filename
    if not p.exists():
        return [Paragraph(f'<b>{label}</b>: Bild konnte beim PDF-Build nicht geladen werden.', styles['Warn']), Paragraph(source_url,styles['Small'])]
    return [img(p,maxh=maxh), Spacer(1,2*mm), Paragraph(f'<b>Originalabbildung / Screenshot-Quelle:</b> {label}<br/>{source_url}',styles['Small'])]

def bullets(items):
    out=[]
    for s in items: out.append(Paragraph('&bull; '+s,styles['Bodyx']))
    return out

def footer(canvas, doc):
    canvas.saveState(); canvas.setFont('Helvetica',7); canvas.setFillColor(colors.HexColor('#777777'))
    canvas.drawString(18*mm,10*mm,'Private Einbauanleitung - 135er Touran - ESP32-S3-CAN-2CH-U')
    canvas.drawRightString(192*mm,10*mm,f'Seite {doc.page}')
    canvas.restoreState()

doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=15*mm,bottomMargin=17*mm,title='Private Einbauanleitung Touran 1T3 ESP32 CAN')
story=[]

story += [Spacer(1,8*mm), Paragraph('PRIVATE EINBAUANLEITUNG',styles['Small']), Paragraph('ESP32-S3-CAN-2CH-U<br/>im VW Touran 1T3',styles['Title2']), Paragraph('Touran 2012 / Projekt 135er Touran - passive CAN-Erfassung',styles['Bodyx']), Spacer(1,5*mm)]
story += source_block('waveshare.jpg','Waveshare Produktfoto','https://github.com/waveshareteam/ESP32-S3-CAN-2CH',75*mm)
story += [Paragraph('Diese Fassung verwendet bewusst echte Abbildungen aus den verlinkten Quellen. Eigene Zeichnungen werden nur fuer den projektspezifischen Anschlussplan verwendet.',styles['Ok']), PageBreak()]

story += [Paragraph('1. Ziel und verbindliche Architektur',styles['H1x']), Wiring(), Spacer(1,4*mm)]
story += bullets([
    '<b>CAN1:</b> Antriebs-CAN, Zielrate 500 kbit/s, erster Test ausschliesslich Listen-Only.',
    '<b>CAN2:</b> Infotainment-CAN am Radio/Quadlock, Zielrate 100 kbit/s, ebenfalls Listen-Only.',
    '<b>ESP -> Erisin:</b> primaer USB. WLAN/BLE bleiben Reserve.',
    '<b>Erisin -> Server:</b> Vodafone-5G-Verbindung fuer Live-Capture-Upload.',
    '<b>Keine 120-Ohm-Zusatzterminierung:</b> der ESP wird als zusaetzlicher Knoten an bestehende Busse angeschlossen.'
])
story += [Paragraph('WICHTIG: Vor jedem Abgriff die Leitung eindeutig identifizieren. Keine Leitung nur anhand einer ungefaehren Lage oder einer einzelnen Farbe anschliessen.',styles['Warn']), PageBreak()]

story += [Paragraph('2. CAN1 - J533 im Fahrerfussraum finden',styles['H1x'])]
story += source_block('j533_trim.jpg','Motor-Talk Bild: Ausbau der unteren Fahrer-Verkleidung','https://www.motor-talk.de/forum/adresse-19-gateway-diagnoseinterface-t2614985.html',78*mm)
story += [Paragraph('Arbeitsweg',styles['H2x'])]
story += bullets([
    'Zuendung aus, Verbraucher aus, Zuendschluessel abziehen.',
    'Ablagefach / untere Verkleidung auf der Fahrerseite ausbauen.',
    'J533 sitzt beim Touran 1T3 ab 08/2010 unterhalb der Schalttafel oberhalb des Relaistraegers.',
    'Nicht am Modul ziehen. Erst Sichtlage, Steckerform und Leitungsfarben dokumentieren.'
])
story += [PageBreak()]

story += [Paragraph('3. J533 - Original VW Ausbauabbildung',styles['H1x'])]
story += source_block('j533_vw.png','VW Touran Reparaturanleitung: J533 aus- und einbauen','https://www.vwtourande.com/diagnose_interface_f_uuml_r_datenbus_j533_aus_und_einbauen-1644.html',118*mm)
story += [Paragraph('Die VW-Anleitung bezeichnet den Stecker als Position 1 und das Diagnose-Interface J533 als Position 2. Fuer unseren Einbau wird J533 <b>nicht ersetzt oder codiert</b>; wir nutzen nur den Leitungsbereich fuer einen passiven Abgriff.',styles['Bodyx']), PageBreak()]

story += [Paragraph('4. CAN1 - T20 / Antriebs-CAN anschliessen',styles['H1x']), Paragraph('Projektzuordnung fuer den geplanten Abgriff:',styles['Bodyx'])]
data=[['T20','Funktion','VW-Farbe','ESP'],['Pin 6','CAN-Low Antrieb','orange/braun','CAN1 L'],['Pin 16','CAN-High Antrieb','orange/schwarz','CAN1 H']]
t=Table(data,colWidths=[25*mm,48*mm,45*mm,35*mm]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#D9EAF7')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#888888')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)])); story += [t,Spacer(1,5*mm)]
story += bullets([
    'Pin-Nummern am realen Steckergehaeuse ablesen; Blickrichtung aus Internetgrafiken niemals blind uebernehmen.',
    'Orange/braun ist bei VW auf mehreren CAN-Netzen Low. Fuer Antrieb ist das Gegenstueck orange/schwarz entscheidend.',
    'Abzweig parallel herstellen; Originalleitung nicht auftrennen.',
    'Neue CAN1-Leitung als verdrilltes Paar fuehren und vom J533 zum ESP hinter Radio/Handschuhfach legen.',
    'Vor dem ersten Einschalten Durchgang, Kurzschlussfreiheit und H/L-Zuordnung pruefen.'
])
story += [Paragraph('Der oben gezeigte Pinplan ist ein projektspezifischer Anschlussplan und keine kopierte Werkstattabbildung.',styles['Small']), PageBreak()]

story += [Paragraph('5. CAN2 - Radio / Quadlock - Originalbilder',styles['H1x'])]
story += source_block('rns_overview.png','VW RNS510: Uebersicht der Steckverbindungen','https://www.vwtourande.com/_uuml_bersicht_uuml_ber_die_steckverbindungen_am_radio_navigationssystem_rns_510_-1187.html',66*mm)
story += source_block('rns_can.png','VW RNS510: Mehrfachsteckverbindung 2 fuer Versorgung und CAN','https://www.vwtourande.com/_uuml_bersicht_uuml_ber_die_steckverbindungen_am_radio_navigationssystem_rns_510_-1187.html',66*mm)
story += [PageBreak()]

story += [Paragraph('6. CAN2 - Pin 9 / 10 erkennen',styles['H1x'])]
story += source_block('rns_pinout.jpg','RNS510/RCD510 Pinout-Foto aus Einbaubeitrag','https://www.drive2.ru/l/8982768/',98*mm)
story += [Paragraph('<b>Fuer den Infotainment-CAN:</b> Pin 9 = CAN-Bus High, Pin 10 = CAN-Bus Low. Der Abgriff erfolgt an der <b>Fahrzeugseite</b> des Quadlocks und nicht an irgendeinem nachgeruesteten Erisin-CAN-Decoder.',styles['Bodyx'])]
story += bullets([
    'Quadlock aus dem Radio loesen und Sektion/Pinzahl am Stecker selbst bestaetigen.',
    'CAN2 H parallel an Pin 9.',
    'CAN2 L parallel an Pin 10.',
    'Leitung als verdrilltes Paar direkt zum ESP fuehren.',
    'Bestehende Erisin-Adapter oder Decoder nicht elektrisch als Referenz fuer die Pinbelegung verwenden.'
])
story += [PageBreak()]

story += [Paragraph('7. ESP32-S3-CAN-2CH-U - Originalfoto',styles['H1x'])]
story += source_block('waveshare_docs.webp','Waveshare Dokumentation / Gehaeuseansicht','https://docs.waveshare.com/ESP32-S3-CAN-2CH',93*mm)
story += [Paragraph('Anschlussbelegung fuer unser Projekt',styles['H2x'])]
data=[['ESP-Anschluss','Touran'],['USB Type-C','USB-A/USB-C Host am Erisin; Daten + Versorgung'],['CAN_1 H / L','Antriebs-CAN vom J533'],['CAN_2 H / L','Infotainment-CAN vom Quadlock'],['7-36 V Klemme','bei USB-Versorgung NICHT verwenden'],['120R CAN1/CAN2','Jumper AUS / offen']]
t=Table(data,colWidths=[55*mm,105*mm]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#D9EAF7')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#888')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8.8),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)])); story += [t]
story += [Paragraph('Waveshare warnt ausdruecklich davor, Schraubklemmenversorgung und USB-Versorgung gleichzeitig zu verwenden. Bei unserem Aufbau bleibt die 7-36-V-Klemme frei, solange das Erisin den ESP ueber USB versorgt.',styles['Warn']), PageBreak()]

story += [Paragraph('8. Einbauort ESP und Leitungsfuehrung',styles['H1x'])]
story += bullets([
    'ESP hinter Handschuhfach / Radio so befestigen, dass USB, CAN-Klemmen und Reset/Boot noch erreichbar bleiben.',
    'Nicht lose auf Metalltraeger legen. Scheuer- und Klapperstellen vermeiden.',
    'CAN1 vom Fahrerfussraum hinter der Mittelkonsole zum ESP fuehren.',
    'CAN2 vom Quadlock nur kurz zum ESP fuehren.',
    'CAN-Leitungen verdrillt lassen bzw. neue Abzweigpaare ebenfalls verdrillen.',
    'Nicht parallel ueber laengere Strecke direkt neben stark stromfuehrenden Leitungen verlegen, wenn eine alternative Route moeglich ist.',
    'Externe Antenne der U-Version so platzieren, dass Metallabschirmung vermieden wird.'
])
story += [Paragraph('Keine 120-Ohm-Jumper setzen. Das Fahrzeugnetz besitzt seine Terminierung bereits. Der ESP ist hier ein zusaetzlicher passiver Knoten.',styles['Warn']), PageBreak()]

story += [Paragraph('9. Schritt-fuer-Schritt Erstinbetriebnahme im Fahrzeug',styles['H1x'])]
steps=[
    ('1','Nur USB anschliessen','ESP bootet, Gateway meldet readonly / tx_hard_blocked.'),
    ('2','Nur CAN1 anschliessen','Zuendung EIN, noch nicht fahren. Framezaehler CAN1 muss steigen.'),
    ('3','Motor starten','Leerlauf aufzeichnen; danach kurz etwa 2000 rpm fuer Differenzanalyse.'),
    ('4','CAN2 zusaetzlich anschliessen','Radio/MFA-Aktionen ausloesen und CAN2-Framezaehler beobachten.'),
    ('5','Live-Upload pruefen','Erisin ueber Vodafone 5G, Session auf Server sichtbar.'),
    ('6','Fahrtest erst danach','Nur wenn keine Busfehler, keine Warnlampen und beide Kanaele stabil sind.')
]
t=Table([[a,b,c] for a,b,c in steps],colWidths=[12*mm,48*mm,100*mm]); t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#AAA')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#E8F2F8')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8.7),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)])); story += [t,Spacer(1,5*mm)]
story += [Paragraph('Wenn bereits beim Anschluss eines einzelnen Busses Warnlampen, Kommunikationsfehler oder ein auffaelliges Busverhalten auftreten: Zuendung aus, ESP trennen und H/L, Abgriff, Terminierung sowie Buszuordnung erneut pruefen.',styles['Warn']), PageBreak()]

story += [Paragraph('10. Capture-Ablauf fuer die Analyse',styles['H1x'])]
story += bullets([
    'Zustand A: Zuendung aus / Busruhe.',
    'Zustand B: Zuendung ein, Motor aus.',
    'Zustand C: Motorstart und Leerlauf.',
    'Zustand D: ca. 2000 rpm fuer einige Sekunden.',
    'Zustand E: Bremse, Blinker links/rechts, Licht, Klima.',
    'Zustand F: MFA hoch/runter/OK, Lenkradtasten, Radioaktionen.',
    'Zustand G: HERE-Navigation spaeter separat, nachdem der reine Empfang bestaetigt ist.'
])
story += [Paragraph('Fuer jede Aktion Zeit oder Reihenfolge notieren. Der Projekt-Analyzer sortiert IDs nach Frequenz und Byte-Aenderungen und kann dadurch Kandidaten wie RPM, Geschwindigkeit oder MFA-Telegramme schneller eingrenzen.',styles['Bodyx']), PageBreak()]

story += [Paragraph('11. Abschluss-Checkliste vor dem Zusammenbau',styles['H1x'])]
checks=[
    'Firmware meldet read-only / tx_hard_blocked.', '120R CAN1 offen.', '120R CAN2 offen.',
    'USB ist die einzige Versorgung.', 'CAN1 H/L verifiziert.', 'CAN2 H/L verifiziert.',
    'Abzweige mechanisch und elektrisch sauber.', 'Leitungen verdrillt und gegen Scheuern gesichert.',
    'ESP befestigt und nicht lose.', 'USB-Stecker zugentlastet.', 'CAN1 Empfang getestet.',
    'CAN2 Empfang getestet.', 'Live-Upload getestet.', 'Keine Warnlampen / neuen Kommunikationsfehler.'
]
for c in checks: story.append(Paragraph('[  ] '+c,styles['Bodyx']))
story += [PageBreak()]

story += [Paragraph('12. Bild- und Informationsquellen',styles['H1x'])]
refs=[
    ('VW Touran J533 Ausbau / Originalgrafik','https://www.vwtourande.com/diagnose_interface_f_uuml_r_datenbus_j533_aus_und_einbauen-1644.html'),
    ('VW Touran J533 allgemeiner Einbauort','https://www.vwtourande.com/allgemeine_beschreibung-1643.html'),
    ('Motor-Talk Fahrerfussraum / Gateway-Zugang','https://www.motor-talk.de/forum/adresse-19-gateway-diagnoseinterface-t2614985.html'),
    ('VW Touran RNS510 Steckverbinder und CAN Pins 9/10','https://www.vwtourande.com/_uuml_bersicht_uuml_ber_die_steckverbindungen_am_radio_navigationssystem_rns_510_-1187.html'),
    ('RNS510/RCD510 Pinout-Bild','https://www.drive2.ru/l/8982768/'),
    ('Waveshare Dokumentation ESP32-S3-CAN-2CH','https://docs.waveshare.com/ESP32-S3-CAN-2CH'),
    ('Waveshare offizielles GitHub Repository','https://github.com/waveshareteam/ESP32-S3-CAN-2CH'),
    ('Waveshare Hardware Reference','https://github.com/waveshareteam/ESP32-S3-CAN-2CH/blob/main/HARDWARE_REFERENCE.md'),
]
for name,url in refs: story += [Paragraph('<b>'+name+'</b><br/>'+url,styles['Small']),Spacer(1,2*mm)]
if failed:
    story += [Spacer(1,4*mm),Paragraph('Hinweis zum automatischen Build',styles['H2x'])]
    for label,url,e in failed: story.append(Paragraph(f'Nicht geladen: {label}<br/>{url}<br/>{e}',styles['Small']))

story += [Spacer(1,5*mm), Paragraph('Nur fuer den privaten Einbau am eigenen Fahrzeug. Vor Arbeiten an Fahrzeugelektrik immer Spannungs- und Leitungszuordnung am realen Fahrzeug verifizieren.',styles['Warn'])]

doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
