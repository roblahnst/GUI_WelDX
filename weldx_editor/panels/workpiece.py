import streamlit as st
import numpy as np
import pandas as pd
from weldx_editor.utils.style import COLORS
from weldx_editor.utils.weldx_io import (
    add_imported_path, remove_imported_path,
)


# Material database for different material groups
# Mechanical properties: minimum values at room temperature, t <= 40 mm
# density in kg/dm³ (= g/cm³)
MATERIALS_DB = {
    # ── Unlegierte Baustähle (EN 10025-2) ──
    "Unlegierte Baustähle": {
        "S235JR (1.0038) — EN 10025-2":   {"yield_strength": 235, "tensile_strength": 360, "density": 7.85},
        "S235J0 (1.0114) — EN 10025-2":   {"yield_strength": 235, "tensile_strength": 360, "density": 7.85},
        "S235J2 (1.0117) — EN 10025-2":   {"yield_strength": 235, "tensile_strength": 360, "density": 7.85},
        "S275JR (1.0044) — EN 10025-2":   {"yield_strength": 275, "tensile_strength": 410, "density": 7.85},
        "S275J0 (1.0143) — EN 10025-2":   {"yield_strength": 275, "tensile_strength": 410, "density": 7.85},
        "S275J2 (1.0145) — EN 10025-2":   {"yield_strength": 275, "tensile_strength": 410, "density": 7.85},
        "S355JR (1.0045) — EN 10025-2":   {"yield_strength": 355, "tensile_strength": 470, "density": 7.85},
        "S355J0 (1.0553) — EN 10025-2":   {"yield_strength": 355, "tensile_strength": 470, "density": 7.85},
        "S355J2 (1.0577) — EN 10025-2":   {"yield_strength": 355, "tensile_strength": 470, "density": 7.85},
        "S355K2 (1.0596) — EN 10025-2":   {"yield_strength": 355, "tensile_strength": 470, "density": 7.85},
        "S450J0 (1.0590) — EN 10025-2":   {"yield_strength": 450, "tensile_strength": 550, "density": 7.85},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Feinkornbaustähle normalgeglüht (EN 10025-3) ──
    "Feinkornbaustähle (N/NL)": {
        "S275N (1.0490) — EN 10025-3":    {"yield_strength": 275, "tensile_strength": 370, "density": 7.85},
        "S275NL (1.0491) — EN 10025-3":   {"yield_strength": 275, "tensile_strength": 370, "density": 7.85},
        "S355N (1.0545) — EN 10025-3":    {"yield_strength": 355, "tensile_strength": 470, "density": 7.85},
        "S355NL (1.0546) — EN 10025-3":   {"yield_strength": 355, "tensile_strength": 470, "density": 7.85},
        "S420N (1.8902) — EN 10025-3":    {"yield_strength": 420, "tensile_strength": 520, "density": 7.85},
        "S420NL (1.8912) — EN 10025-3":   {"yield_strength": 420, "tensile_strength": 520, "density": 7.85},
        "S460N (1.8901) — EN 10025-3":    {"yield_strength": 460, "tensile_strength": 540, "density": 7.85},
        "S460NL (1.8903) — EN 10025-3":   {"yield_strength": 460, "tensile_strength": 540, "density": 7.85},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Feinkornbaustähle thermomechanisch (EN 10025-4) ──
    "Feinkornbaustähle (M/ML)": {
        "S275M (1.8818) — EN 10025-4":    {"yield_strength": 275, "tensile_strength": 370, "density": 7.85},
        "S275ML (1.8819) — EN 10025-4":   {"yield_strength": 275, "tensile_strength": 370, "density": 7.85},
        "S355M (1.8823) — EN 10025-4":    {"yield_strength": 355, "tensile_strength": 470, "density": 7.85},
        "S355ML (1.8834) — EN 10025-4":   {"yield_strength": 355, "tensile_strength": 470, "density": 7.85},
        "S420M (1.8825) — EN 10025-4":    {"yield_strength": 420, "tensile_strength": 520, "density": 7.85},
        "S420ML (1.8836) — EN 10025-4":   {"yield_strength": 420, "tensile_strength": 520, "density": 7.85},
        "S460M (1.8827) — EN 10025-4":    {"yield_strength": 460, "tensile_strength": 540, "density": 7.85},
        "S460ML (1.8838) — EN 10025-4":   {"yield_strength": 460, "tensile_strength": 540, "density": 7.85},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Hochfeste vergütete Baustähle (EN 10025-6) ──
    "Hochfeste Baustähle (QL)": {
        "S460Q (1.8908) — EN 10025-6":    {"yield_strength": 460, "tensile_strength": 550, "density": 7.85},
        "S460QL (1.8906) — EN 10025-6":   {"yield_strength": 460, "tensile_strength": 550, "density": 7.85},
        "S460QL1 (1.8916) — EN 10025-6":  {"yield_strength": 460, "tensile_strength": 550, "density": 7.85},
        "S500Q (1.8924) — EN 10025-6":    {"yield_strength": 500, "tensile_strength": 590, "density": 7.85},
        "S500QL (1.8909) — EN 10025-6":   {"yield_strength": 500, "tensile_strength": 590, "density": 7.85},
        "S500QL1 (1.8984) — EN 10025-6":  {"yield_strength": 500, "tensile_strength": 590, "density": 7.85},
        "S550Q (1.8904) — EN 10025-6":    {"yield_strength": 550, "tensile_strength": 640, "density": 7.85},
        "S550QL (1.8926) — EN 10025-6":   {"yield_strength": 550, "tensile_strength": 640, "density": 7.85},
        "S620Q (1.8914) — EN 10025-6":    {"yield_strength": 620, "tensile_strength": 700, "density": 7.85},
        "S620QL (1.8927) — EN 10025-6":   {"yield_strength": 620, "tensile_strength": 700, "density": 7.85},
        "S690Q (1.8931) — EN 10025-6":    {"yield_strength": 690, "tensile_strength": 770, "density": 7.85},
        "S690QL (1.8928) — EN 10025-6":   {"yield_strength": 690, "tensile_strength": 770, "density": 7.85},
        "S690QL1 (1.8988) — EN 10025-6":  {"yield_strength": 690, "tensile_strength": 770, "density": 7.85},
        "S890QL (1.8983) — EN 10025-6":   {"yield_strength": 890, "tensile_strength": 940, "density": 7.85},
        "S890QL1 (1.8985) — EN 10025-6":  {"yield_strength": 890, "tensile_strength": 940, "density": 7.85},
        "S960QL (1.8933) — EN 10025-6":   {"yield_strength": 960, "tensile_strength": 980, "density": 7.85},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Warmgewalzte höherfeste Stähle (EN 10149-2) ──
    "Höherfeste Stähle zum Kaltumformen": {
        "S315MC (1.0972) — EN 10149-2":   {"yield_strength": 315, "tensile_strength": 390, "density": 7.85},
        "S355MC (1.0976) — EN 10149-2":   {"yield_strength": 355, "tensile_strength": 430, "density": 7.85},
        "S420MC (1.0980) — EN 10149-2":   {"yield_strength": 420, "tensile_strength": 480, "density": 7.85},
        "S460MC (1.0982) — EN 10149-2":   {"yield_strength": 460, "tensile_strength": 520, "density": 7.85},
        "S500MC (1.0984) — EN 10149-2":   {"yield_strength": 500, "tensile_strength": 550, "density": 7.85},
        "S550MC (1.0986) — EN 10149-2":   {"yield_strength": 550, "tensile_strength": 600, "density": 7.85},
        "S600MC (1.8969) — EN 10149-2":   {"yield_strength": 600, "tensile_strength": 650, "density": 7.85},
        "S650MC (1.8976) — EN 10149-2":   {"yield_strength": 650, "tensile_strength": 700, "density": 7.85},
        "S700MC (1.8974) — EN 10149-2":   {"yield_strength": 700, "tensile_strength": 750, "density": 7.85},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Druckbehälterstähle (EN 10028-2/3/7) ──
    "Druckbehälterstähle": {
        "P235GH (1.0345) — EN 10028-2":        {"yield_strength": 235, "tensile_strength": 360, "density": 7.85},
        "P265GH (1.0425) — EN 10028-2":        {"yield_strength": 265, "tensile_strength": 410, "density": 7.85},
        "P295GH (1.0481) — EN 10028-2":        {"yield_strength": 295, "tensile_strength": 460, "density": 7.85},
        "P355GH (1.0473) — EN 10028-2":        {"yield_strength": 355, "tensile_strength": 490, "density": 7.85},
        "16Mo3 (1.5415) — EN 10028-2":         {"yield_strength": 270, "tensile_strength": 440, "density": 7.85},
        "13CrMo4-5 (1.7335) — EN 10028-2":    {"yield_strength": 290, "tensile_strength": 440, "density": 7.85},
        "10CrMo9-10 (1.7380) — EN 10028-2":   {"yield_strength": 280, "tensile_strength": 450, "density": 7.85},
        "P275NH (1.0487) — EN 10028-3":        {"yield_strength": 275, "tensile_strength": 390, "density": 7.85},
        "P355NH (1.0565) — EN 10028-3":        {"yield_strength": 355, "tensile_strength": 490, "density": 7.85},
        "P355NL1 (1.0566) — EN 10028-3":       {"yield_strength": 355, "tensile_strength": 490, "density": 7.85},
        "P460NH (1.8935) — EN 10028-3":        {"yield_strength": 460, "tensile_strength": 560, "density": 7.85},
        "P460NL1 (1.8915) — EN 10028-3":       {"yield_strength": 460, "tensile_strength": 560, "density": 7.85},
        "X7Ni9 (1.5663) — EN 10028-4":         {"yield_strength": 390, "tensile_strength": 640, "density": 7.85},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Warmfeste Stähle (EN 10216-2, EN 10222) ──
    "Warmfeste Stähle": {
        "P235GH (1.0345) — EN 10216-2":          {"yield_strength": 235, "tensile_strength": 360, "density": 7.85},
        "P250GH (1.0460) — EN 10216-2":          {"yield_strength": 250, "tensile_strength": 400, "density": 7.85},
        "16Mo3 (1.5415) — EN 10216-2":           {"yield_strength": 270, "tensile_strength": 440, "density": 7.85},
        "13CrMo4-5 (1.7335) — EN 10216-2":      {"yield_strength": 290, "tensile_strength": 440, "density": 7.85},
        "10CrMo9-10 (1.7380) — EN 10216-2":     {"yield_strength": 280, "tensile_strength": 450, "density": 7.85},
        "X11CrMo9-1 (1.7386) — EN 10216-2":     {"yield_strength": 280, "tensile_strength": 480, "density": 7.85},
        "X10CrMoVNb9-1 (1.4903) — EN 10216-2":  {"yield_strength": 450, "tensile_strength": 630, "density": 7.76},
        "X20CrMoV11-1 (1.4922) — EN 10216-2":   {"yield_strength": 490, "tensile_strength": 690, "density": 7.70},
        "7CrWVMoNb9-6 (1.8201) — EN 10216-2":   {"yield_strength": 450, "tensile_strength": 620, "density": 7.75},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Nichtrostende Stähle — austenitisch (EN 10088-2) ──
    "Nichtrostende Stähle (austenitisch)": {
        "X2CrNi18-9 (1.4307) — EN 10088-2":           {"yield_strength": 200, "tensile_strength": 500, "density": 7.90},
        "X5CrNi18-10 (1.4301) — EN 10088-2":          {"yield_strength": 210, "tensile_strength": 520, "density": 7.90},
        "X8CrNiS18-9 (1.4305) — EN 10088-2":          {"yield_strength": 190, "tensile_strength": 500, "density": 7.90},
        "X6CrNiTi18-10 (1.4541) — EN 10088-2":        {"yield_strength": 200, "tensile_strength": 500, "density": 7.90},
        "X6CrNiNb18-10 (1.4550) — EN 10088-2":        {"yield_strength": 200, "tensile_strength": 500, "density": 7.90},
        "X2CrNiMo17-12-2 (1.4404) — EN 10088-2":      {"yield_strength": 220, "tensile_strength": 520, "density": 8.00},
        "X5CrNiMo17-12-2 (1.4401) — EN 10088-2":      {"yield_strength": 220, "tensile_strength": 520, "density": 8.00},
        "X6CrNiMoTi17-12-2 (1.4571) — EN 10088-2":    {"yield_strength": 220, "tensile_strength": 520, "density": 8.00},
        "X2CrNiMo18-14-3 (1.4435) — EN 10088-2":      {"yield_strength": 220, "tensile_strength": 520, "density": 8.00},
        "X2CrNiMoN17-13-3 (1.4429) — EN 10088-2":     {"yield_strength": 280, "tensile_strength": 580, "density": 8.00},
        "X1CrNiMoN25-22-2 (1.4466) — EN 10088-2":     {"yield_strength": 300, "tensile_strength": 600, "density": 8.00},
        "X1NiCrMoCu25-20-5 (1.4539) — EN 10088-2":    {"yield_strength": 220, "tensile_strength": 520, "density": 8.00},
        "X2CrNiMoN17-13-5 (1.4439) — EN 10088-2":     {"yield_strength": 270, "tensile_strength": 580, "density": 8.00},
        "X1NiCrMoCuN20-18-7 (1.4547) — EN 10088-2":   {"yield_strength": 300, "tensile_strength": 650, "density": 8.10},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Nichtrostende Stähle — ferritisch (EN 10088-2) ──
    "Nichtrostende Stähle (ferritisch)": {
        "X2CrNi12 (1.4003) — EN 10088-2":             {"yield_strength": 250, "tensile_strength": 450, "density": 7.70},
        "X6Cr17 (1.4016) — EN 10088-2":               {"yield_strength": 260, "tensile_strength": 430, "density": 7.70},
        "X3CrTi17 (1.4510) — EN 10088-2":             {"yield_strength": 230, "tensile_strength": 420, "density": 7.70},
        "X2CrMoTi18-2 (1.4521) — EN 10088-2":         {"yield_strength": 300, "tensile_strength": 420, "density": 7.70},
        "X6CrMoS17 (1.4105) — EN 10088-2":            {"yield_strength": 260, "tensile_strength": 430, "density": 7.70},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Nichtrostende Stähle — martensitisch (EN 10088-2) ──
    "Nichtrostende Stähle (martensitisch)": {
        "X12Cr13 (1.4006) — EN 10088-2":               {"yield_strength": 400, "tensile_strength": 650, "density": 7.70},
        "X20Cr13 (1.4021) — EN 10088-2":               {"yield_strength": 500, "tensile_strength": 700, "density": 7.70},
        "X30Cr13 (1.4028) — EN 10088-2":               {"yield_strength": 600, "tensile_strength": 800, "density": 7.70},
        "X17CrNi16-2 (1.4057) — EN 10088-2":          {"yield_strength": 550, "tensile_strength": 750, "density": 7.70},
        "X3CrNiMo13-4 (1.4313) — EN 10088-2":         {"yield_strength": 580, "tensile_strength": 780, "density": 7.70},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Nichtrostende Stähle — Duplex/Super-Duplex (EN 10088-2) ──
    "Nichtrostende Stähle (Duplex)": {
        "X2CrNiN23-4 (1.4362) — EN 10088-2":          {"yield_strength": 400, "tensile_strength": 600, "density": 7.80},
        "X2CrNiMoN22-5-3 (1.4462) — EN 10088-2":     {"yield_strength": 450, "tensile_strength": 650, "density": 7.80},
        "X2CrNiMoSi18-5-3 (1.4424) — EN 10088-2":    {"yield_strength": 450, "tensile_strength": 650, "density": 7.80},
        "X2CrNiMoN25-7-4 (1.4410) — EN 10088-2":     {"yield_strength": 530, "tensile_strength": 730, "density": 7.80},
        "X2CrNiMoCuWN25-7-4 (1.4501) — EN 10088-2":  {"yield_strength": 530, "tensile_strength": 730, "density": 7.85},
        "X2CrMnNiN21-5-1 (1.4162) — EN 10088-2":     {"yield_strength": 450, "tensile_strength": 650, "density": 7.80},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Rohrleitungsstähle (EN 10208-2 / API 5L) ──
    "Rohrleitungsstähle": {
        "L210GA (1.0308) — EN 10208-2":                  {"yield_strength": 210, "tensile_strength": 335, "density": 7.85},
        "L245NB (1.0457) — EN 10208-2 / API 5L Gr B":   {"yield_strength": 245, "tensile_strength": 415, "density": 7.85},
        "L290NB (1.0484) — EN 10208-2 / API 5L X42":    {"yield_strength": 290, "tensile_strength": 415, "density": 7.85},
        "L360NB (1.0582) — EN 10208-2 / API 5L X52":    {"yield_strength": 360, "tensile_strength": 460, "density": 7.85},
        "L390MB (1.8960) — EN 10208-2 / API 5L X56":    {"yield_strength": 390, "tensile_strength": 490, "density": 7.85},
        "L415NB (1.8972) — EN 10208-2 / API 5L X60":    {"yield_strength": 415, "tensile_strength": 520, "density": 7.85},
        "L450MB (1.8975) — EN 10208-2 / API 5L X65":    {"yield_strength": 450, "tensile_strength": 535, "density": 7.85},
        "L485MB (1.8977) — EN 10208-2 / API 5L X70":    {"yield_strength": 485, "tensile_strength": 570, "density": 7.85},
        "L555MB (1.8978) — EN 10208-2 / API 5L X80":    {"yield_strength": 555, "tensile_strength": 625, "density": 7.85},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Aluminium-Knetlegierungen (EN 573-3, EN 485, EN 755) ──
    "Aluminium-Knetlegierungen": {
        "EN AW-1050A (Al 99.5) H14 — EN 573-3":     {"yield_strength": 85,  "tensile_strength": 105, "density": 2.71},
        "EN AW-1100 (Al 99.0Cu) H14 — EN 573-3":    {"yield_strength": 95,  "tensile_strength": 110, "density": 2.71},
        "EN AW-2017A T4 (AlCu4MgSi) — EN 573-3":    {"yield_strength": 270, "tensile_strength": 420, "density": 2.79},
        "EN AW-2024 T3 (AlCu4Mg1) — EN 573-3":      {"yield_strength": 345, "tensile_strength": 485, "density": 2.78},
        "EN AW-3003 H14 (AlMn1Cu) — EN 573-3":       {"yield_strength": 120, "tensile_strength": 145, "density": 2.73},
        "EN AW-5005 H34 (AlMg1) — EN 573-3":         {"yield_strength": 120, "tensile_strength": 145, "density": 2.70},
        "EN AW-5052 H32 (AlMg2.5) — EN 573-3":       {"yield_strength": 160, "tensile_strength": 230, "density": 2.68},
        "EN AW-5083 H111 (AlMg4.5Mn) — EN 573-3":    {"yield_strength": 125, "tensile_strength": 275, "density": 2.66},
        "EN AW-5086 H116 (AlMg4) — EN 573-3":        {"yield_strength": 195, "tensile_strength": 275, "density": 2.66},
        "EN AW-5754 H22 (AlMg3) — EN 573-3":         {"yield_strength": 130, "tensile_strength": 220, "density": 2.67},
        "EN AW-6060 T6 (AlMgSi) — EN 573-3":         {"yield_strength": 150, "tensile_strength": 190, "density": 2.70},
        "EN AW-6061 T6 (AlMg1SiCu) — EN 573-3":      {"yield_strength": 275, "tensile_strength": 310, "density": 2.70},
        "EN AW-6063 T6 (AlMg0.7Si) — EN 573-3":       {"yield_strength": 170, "tensile_strength": 215, "density": 2.70},
        "EN AW-6082 T6 (AlSi1MgMn) — EN 573-3":       {"yield_strength": 260, "tensile_strength": 310, "density": 2.71},
        "EN AW-7020 T6 (AlZn4.5Mg1) — EN 573-3":      {"yield_strength": 280, "tensile_strength": 350, "density": 2.78},
        "EN AW-7075 T6 (AlZn5.5MgCu) — EN 573-3":     {"yield_strength": 503, "tensile_strength": 572, "density": 2.81},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Aluminium-Gusslegierungen (EN 1706) ──
    "Aluminium-Gusslegierungen": {
        "EN AC-42100 (AlSi7Mg0.3) T6 — EN 1706":    {"yield_strength": 210, "tensile_strength": 260, "density": 2.68},
        "EN AC-42200 (AlSi7Mg0.6) T6 — EN 1706":    {"yield_strength": 240, "tensile_strength": 290, "density": 2.68},
        "EN AC-43000 (AlSi10Mg) F — EN 1706":        {"yield_strength": 90,  "tensile_strength": 180, "density": 2.65},
        "EN AC-44200 (AlSi12) F — EN 1706":          {"yield_strength": 80,  "tensile_strength": 170, "density": 2.65},
        "EN AC-46200 (AlSi8Cu3) F — EN 1706":        {"yield_strength": 100, "tensile_strength": 200, "density": 2.75},
        "EN AC-51300 (AlMg5) F — EN 1706":           {"yield_strength": 110, "tensile_strength": 200, "density": 2.65},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Nickellegierungen (EN 10095, ASTM / UNS) ──
    "Nickellegierungen": {
        "Alloy 200 / Ni 200 (2.4066) — UNS N02200":          {"yield_strength": 100, "tensile_strength": 380, "density": 8.89},
        "Alloy 201 / Ni 201 (2.4068) — UNS N02201":          {"yield_strength": 70,  "tensile_strength": 345, "density": 8.89},
        "Alloy 400 / Monel 400 (2.4360) — UNS N04400":       {"yield_strength": 230, "tensile_strength": 550, "density": 8.83},
        "Alloy K-500 / Monel K-500 (2.4375) — UNS N05500":   {"yield_strength": 690, "tensile_strength": 1000, "density": 8.44},
        "Alloy 600 / Inconel 600 (2.4816) — UNS N06600":     {"yield_strength": 240, "tensile_strength": 550, "density": 8.47},
        "Alloy 601 / Inconel 601 (2.4851) — UNS N06601":     {"yield_strength": 205, "tensile_strength": 550, "density": 8.11},
        "Alloy 617 / Inconel 617 (2.4663) — UNS N06617":     {"yield_strength": 295, "tensile_strength": 655, "density": 8.36},
        "Alloy 625 / Inconel 625 (2.4856) — UNS N06625":     {"yield_strength": 414, "tensile_strength": 827, "density": 8.44},
        "Alloy 718 / Inconel 718 (2.4668) — UNS N07718":     {"yield_strength": 1034, "tensile_strength": 1241, "density": 8.19},
        "Alloy 825 / Incoloy 825 (2.4858) — UNS N08825":     {"yield_strength": 241, "tensile_strength": 586, "density": 8.14},
        "Alloy C-276 / Hastelloy C-276 (2.4819) — UNS N10276":  {"yield_strength": 310, "tensile_strength": 690, "density": 8.89},
        "Alloy C-22 / Hastelloy C-22 (2.4602) — UNS N06022":   {"yield_strength": 310, "tensile_strength": 690, "density": 8.69},
        "Alloy B-2 / Hastelloy B-2 (2.4617) — UNS N10665":     {"yield_strength": 345, "tensile_strength": 760, "density": 9.22},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Titanlegierungen (ASTM B265, ISO 5832) ──
    "Titanlegierungen": {
        "Ti Grade 1 (3.7025) — ASTM B265":            {"yield_strength": 170, "tensile_strength": 240, "density": 4.51},
        "Ti Grade 2 (3.7035) — ASTM B265":            {"yield_strength": 275, "tensile_strength": 345, "density": 4.51},
        "Ti Grade 3 (3.7055) — ASTM B265":            {"yield_strength": 380, "tensile_strength": 450, "density": 4.51},
        "Ti Grade 4 (3.7065) — ASTM B265":            {"yield_strength": 480, "tensile_strength": 550, "density": 4.51},
        "Ti Grade 7 (3.7235) — ASTM B265":            {"yield_strength": 275, "tensile_strength": 345, "density": 4.51},
        "Ti Grade 12 (3.7105) — ASTM B265":           {"yield_strength": 345, "tensile_strength": 480, "density": 4.51},
        "Ti-6Al-4V Grade 5 (3.7164) — ASTM B265":    {"yield_strength": 880, "tensile_strength": 950, "density": 4.43},
        "Ti-6Al-4V ELI Grade 23 (3.7165) — ASTM B265": {"yield_strength": 795, "tensile_strength": 860, "density": 4.43},
        "Ti-3Al-2.5V Grade 9 (3.7195) — ASTM B265":  {"yield_strength": 485, "tensile_strength": 620, "density": 4.48},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
    # ── Kupferlegierungen (EN 1652, EN 12163, EN 12420) ──
    "Kupferlegierungen": {
        "Cu-OF (CW008A) R220 — EN 1652":              {"yield_strength": 50,  "tensile_strength": 220, "density": 8.94},
        "Cu-DHP (CW024A) R220 — EN 1652":             {"yield_strength": 60,  "tensile_strength": 220, "density": 8.90},
        "CuZn37 (CW508L) R370 — EN 12163":            {"yield_strength": 180, "tensile_strength": 370, "density": 8.44},
        "CuZn39Pb3 (CW614N) R400 — EN 12163":         {"yield_strength": 200, "tensile_strength": 400, "density": 8.47},
        "CuSn6 (CW452K) R400 — EN 1652":              {"yield_strength": 200, "tensile_strength": 400, "density": 8.80},
        "CuSn8 (CW453K) R470 — EN 1652":              {"yield_strength": 270, "tensile_strength": 470, "density": 8.80},
        "CuAl8Fe3 (CW304G) R550 — EN 12163":          {"yield_strength": 250, "tensile_strength": 550, "density": 7.60},
        "CuAl10Ni5Fe4 (CW307G) R640 — EN 12163":      {"yield_strength": 300, "tensile_strength": 640, "density": 7.58},
        "CuNi10Fe1Mn (CW352H) R350 — EN 1652":        {"yield_strength": 120, "tensile_strength": 350, "density": 8.90},
        "CuNi30Mn1Fe (CW354H) R400 — EN 1652":        {"yield_strength": 150, "tensile_strength": 400, "density": 8.95},
        "Benutzerdefiniert": {"yield_strength": None, "tensile_strength": None, "density": None},
    },
}

GROOVE_TYPES = {
    "V-Naht":               ["alpha", "b", "c"],
    "I-Naht":               ["b"],
    "HV-Naht":              ["beta", "b", "c"],
    "U-Naht":               ["beta", "R", "c", "b"],
    "HU-Naht":              ["beta", "R", "c", "b"],
    "VV-Naht (V + HV)":     ["alpha", "beta", "h", "c", "b"],
    "UV-Naht (U + HV)":     ["alpha", "beta", "R", "h", "b"],
    "X-Naht (Doppel-V)":    ["alpha_1", "alpha_2", "h1", "h2", "c", "b"],
    "Doppel-HV-Naht":       ["beta_1", "beta_2", "h1", "h2", "c", "b"],
    "Doppel-U-Naht":        ["beta_1", "beta_2", "R", "R2", "h1", "h2", "c", "b"],
    "Doppel-HU-Naht":       ["beta_1", "beta_2", "R", "R2", "h1", "h2", "c", "b"],
    "Bördelnaht":           ["t_1", "t_2", "alpha", "b", "e", "code_number"],
    "Kehlnaht":             ["t_1", "t_2", "alpha", "b", "e", "code_number"],
}



def _get_groove_object(groove_type: str, params: dict):
    """Create a WeldX groove object using the ISO 9692-1 API."""
    try:
        from weldx import Q_
        from weldx.welding.groove.iso_9692_1 import get_groove
        from weldx.welding.groove import iso_9692_1

        t = Q_(params.get("t", 10), "mm")

        if groove_type == "V-Naht":
            return get_groove(groove_type="VGroove", workpiece_thickness=t,
                groove_angle=Q_(params.get("alpha", 60), "deg"),
                root_face=Q_(params.get("c", 1), "mm"),
                root_gap=Q_(params.get("b", 2), "mm"))

        elif groove_type == "I-Naht":
            return get_groove(groove_type="IGroove", workpiece_thickness=t,
                root_gap=Q_(params.get("b", 2), "mm"))

        elif groove_type == "HV-Naht":
            return get_groove(groove_type="HVGroove", workpiece_thickness=t,
                bevel_angle=Q_(params.get("beta", 50), "deg"),
                root_face=Q_(params.get("c", 1), "mm"),
                root_gap=Q_(params.get("b", 2), "mm"))

        elif groove_type == "U-Naht":
            return get_groove(groove_type="UGroove", workpiece_thickness=t,
                bevel_angle=Q_(params.get("beta", 8), "deg"),
                bevel_radius=Q_(params.get("R", 6), "mm"),
                root_face=Q_(params.get("c", 1), "mm"),
                root_gap=Q_(params.get("b", 2), "mm"))

        elif groove_type == "HU-Naht":
            return get_groove(groove_type="HUGroove", workpiece_thickness=t,
                bevel_angle=Q_(params.get("beta", 8), "deg"),
                bevel_radius=Q_(params.get("R", 6), "mm"),
                root_face=Q_(params.get("c", 1), "mm"),
                root_gap=Q_(params.get("b", 2), "mm"))

        elif groove_type == "VV-Naht (V + HV)":
            # VVGroove needs direct construction (get_groove doesn't map 'h')
            return iso_9692_1.VVGroove(t=t,
                alpha=Q_(params.get("alpha", 60), "deg"),
                beta=Q_(params.get("beta", 10), "deg"),
                h=Q_(params.get("h", 4), "mm"),
                c=Q_(params.get("c", 1), "mm"),
                b=Q_(params.get("b", 2), "mm"))

        elif groove_type == "UV-Naht (U + HV)":
            return get_groove(groove_type="UVGroove", workpiece_thickness=t,
                groove_angle=Q_(params.get("alpha", 60), "deg"),
                bevel_angle=Q_(params.get("beta", 8), "deg"),
                bevel_radius=Q_(params.get("R", 6), "mm"),
                special_depth=Q_(params.get("h", 4), "mm"),
                root_gap=Q_(params.get("b", 2), "mm"))

        elif groove_type == "X-Naht (Doppel-V)":
            return get_groove(groove_type="DVGroove", workpiece_thickness=t,
                groove_angle=Q_(params.get("alpha_1", 50), "deg"),
                groove_angle2=Q_(params.get("alpha_2", 60), "deg"),
                root_face=Q_(params.get("c", 2), "mm"),
                special_depth=Q_(params.get("h1", 0), "mm") if params.get("h1") else None,
                root_gap=Q_(params.get("b", 2), "mm"))

        elif groove_type == "Doppel-HV-Naht":
            return get_groove(groove_type="DHVGroove", workpiece_thickness=t,
                bevel_angle=Q_(params.get("beta_1", 50), "deg"),
                bevel_angle2=Q_(params.get("beta_2", 60), "deg"),
                root_face=Q_(params.get("c", 2), "mm"),
                special_depth=Q_(params.get("h1", 0), "mm") if params.get("h1") else None,
                root_gap=Q_(params.get("b", 2), "mm"))

        elif groove_type == "Doppel-U-Naht":
            return get_groove(groove_type="DUGroove", workpiece_thickness=t,
                bevel_angle=Q_(params.get("beta_1", 8), "deg"),
                bevel_angle2=Q_(params.get("beta_2", 10), "deg"),
                bevel_radius=Q_(params.get("R", 6), "mm"),
                bevel_radius2=Q_(params.get("R2", 6), "mm"),
                root_face=Q_(params.get("c", 2), "mm"),
                special_depth=Q_(params.get("h1", 0), "mm") if params.get("h1") else None,
                root_gap=Q_(params.get("b", 2), "mm"))

        elif groove_type == "Doppel-HU-Naht":
            return get_groove(groove_type="DHUGroove", workpiece_thickness=t,
                bevel_angle=Q_(params.get("beta_1", 8), "deg"),
                bevel_angle2=Q_(params.get("beta_2", 10), "deg"),
                bevel_radius=Q_(params.get("R", 6), "mm"),
                bevel_radius2=Q_(params.get("R2", 6), "mm"),
                root_face=Q_(params.get("c", 2), "mm"),
                special_depth=Q_(params.get("h1", 0), "mm") if params.get("h1") else None,
                root_gap=Q_(params.get("b", 2), "mm"))

        elif groove_type in ("Bördelnaht", "Kehlnaht"):
            code = params.get("code_number", "1.12" if groove_type == "Bördelnaht" else "3.1.2")
            return iso_9692_1.FFGroove(
                t_1=Q_(params.get("t_1", 3), "mm"),
                t_2=Q_(params.get("t_2", 3), "mm"),
                alpha=Q_(params.get("alpha", 12 if groove_type == "Bördelnaht" else 45), "deg"),
                b=Q_(params.get("b", 1), "mm"),
                e=Q_(params.get("e", 2), "mm"),
                code_number=code,
            )

        return None
    except ImportError:
        return None
    except Exception as e:
        st.warning(f"Fehler beim Erstellen des Nutobjekts: {e}")
        return None


def _render_basismaterial_tab(state):
    """Render the base material tab."""
    st.subheader("Basismaterial")

    # Initialize base_metal if not present
    if not hasattr(state, "base_metal") or state.base_metal is None:
        state.base_metal = {
            "material_group": "Stähle",
            "material": None,
            "plate_thickness": 10.0,
        }

    # Show info if material was detected from metadata
    designation = state.base_metal.get("designation", "")
    if designation:
        st.success(f"✅ Material aus Datei erkannt: **{designation}**")

    col1, col2 = st.columns(2)

    with col1:
        material_group = st.radio(
            "Werkstoffgruppe:",
            list(MATERIALS_DB.keys()),
            index=list(MATERIALS_DB.keys()).index(state.base_metal.get("material_group", "Unlegierte Baustähle"))
            if state.base_metal.get("material_group", "Unlegierte Baustähle") in MATERIALS_DB
            else 0,
        )
        state.base_metal["material_group"] = material_group

    with col2:
        available_materials = list(MATERIALS_DB[material_group].keys())
        selected_material = st.selectbox(
            "Werkstoff:",
            available_materials,
            index=available_materials.index(state.base_metal.get("material", available_materials[0]))
            if state.base_metal.get("material") in available_materials
            else 0,
        )
        state.base_metal["material"] = selected_material

    plate_thickness = st.number_input(
        "Blechdicke (mm):",
        min_value=0.5,
        max_value=100.0,
        value=float(state.base_metal.get("plate_thickness", 10.0)),
        step=0.5,
    )
    state.base_metal["plate_thickness"] = plate_thickness

    # Display material properties if available
    if selected_material and selected_material != "Benutzerdefiniert":
        props = MATERIALS_DB[material_group][selected_material]
        if props["yield_strength"] is not None:
            info_text = f"""
            **Werkstoffeigenschaften:**
            - Streckgrenze: {props['yield_strength']} MPa
            - Zugfestigkeit: {props['tensile_strength']} MPa
            - Dichte: {props['density']} kg/dm\u00b3
            """
            st.info(info_text)
    else:
        custom_name = st.text_input(
            "Werkstoffbezeichnung:",
            value=state.base_metal.get("designation", ""),
            key="custom_designation",
            placeholder="z.B. X5CrNi13-4 (1.4313)",
        )
        state.base_metal["designation"] = custom_name
        st.markdown("**Werkstoffeigenschaften:**")
        custom = state.base_metal.get("custom_props", {})
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            ys = st.number_input(
                "Streckgrenze (MPa):",
                min_value=0.0, max_value=3000.0,
                value=float(custom.get("yield_strength", 0.0)),
                step=5.0, key="custom_yield",
            )
        with col_b:
            ts = st.number_input(
                "Zugfestigkeit (MPa):",
                min_value=0.0, max_value=3000.0,
                value=float(custom.get("tensile_strength", 0.0)),
                step=5.0, key="custom_tensile",
            )
        with col_c:
            raw_dens = float(custom.get("density", 7.85))
            # Migrate old kg/m³ values to kg/dm³
            if raw_dens > 25.0:
                raw_dens = raw_dens / 1000.0
            dens = st.number_input(
                "Dichte (kg/dm\u00b3):",
                min_value=0.0, max_value=25.0,
                value=raw_dens,
                step=0.01, key="custom_density", format="%.2f",
            )
        state.base_metal["custom_props"] = {
            "yield_strength": ys,
            "tensile_strength": ts,
            "density": dens,
        }


def _render_groove_tab(state):
    """Render the groove geometry tab."""
    st.subheader("Nahtgeometrie (ISO 9692-1)")

    # Initialize groove if not present
    if not hasattr(state, "groove") or state.groove is None:
        state.groove = {
            "type": "V-Naht",
            "params": {},
        }

    groove_type = st.selectbox(
        "Nahttyp:",
        list(GROOVE_TYPES.keys()),
        index=list(GROOVE_TYPES.keys()).index(state.groove.get("type", "V-Naht"))
        if isinstance(state.groove, dict)
        else 0,
    )

    if isinstance(state.groove, dict):
        # Reset params when groove type changes
        old_type = state.groove.get("type")
        state.groove["type"] = groove_type
        if old_type != groove_type:
            state.groove["params"] = {}
        elif "params" not in state.groove:
            state.groove["params"] = {}
    else:
        state.groove = {"type": groove_type, "params": {}}

    # Render parameter inputs based on groove type
    st.markdown("**Parameter:**")
    params = state.groove.get("params", {})

    if groove_type == "V-Naht":
        alpha = st.number_input(
            "Öffnungswinkel α (°):",
            min_value=10.0,
            max_value=90.0,
            value=params.get("alpha", 60.0),
            step=1.0,
        )
        b = st.number_input(
            "Spalt b (mm):",
            min_value=0.5,
            max_value=20.0,
            value=params.get("b", 2.0),
            step=0.5,
        )
        c = st.number_input(
            "Steg c (mm):",
            min_value=0.0,
            max_value=10.0,
            value=params.get("c", 1.0),
            step=0.5,
        )
        params = {"alpha": alpha, "b": b, "c": c}

    elif groove_type == "I-Naht":
        b = st.number_input(
            "Spalt b (mm):",
            min_value=0.5,
            max_value=20.0,
            value=params.get("b", 2.0),
            step=0.5,
        )
        params = {"b": b}

    elif groove_type == "HV-Naht":
        beta = st.number_input(
            "Flankenwinkel β (°):",
            min_value=5.0,
            max_value=90.0,
            value=params.get("beta", 50.0),
            step=1.0,
            help="Winkel der angeschrägten Seite (die andere Seite bleibt senkrecht)",
        )
        b = st.number_input(
            "Spalt b (mm):",
            min_value=0.0,
            max_value=20.0,
            value=params.get("b", 2.0),
            step=0.5,
        )
        c = st.number_input(
            "Steg c (mm):",
            min_value=0.0,
            max_value=10.0,
            value=params.get("c", 1.0),
            step=0.5,
        )
        params = {"beta": beta, "b": b, "c": c}

    elif groove_type == "U-Naht":
        beta = st.number_input(
            "Flankenwinkel β (°):",
            min_value=0.0,
            max_value=45.0,
            value=params.get("beta", 8.0),
            step=1.0,
            help="Winkel der Flanken oberhalb des Radius",
        )
        R = st.number_input(
            "Radius R (mm):",
            min_value=1.0,
            max_value=30.0,
            value=params.get("R", 6.0),
            step=0.5,
            help="Rundungsradius am Nutgrund",
        )
        c = st.number_input(
            "Steg c (mm):",
            min_value=0.0,
            max_value=10.0,
            value=params.get("c", 1.0),
            step=0.5,
        )
        b = st.number_input(
            "Spalt b (mm):",
            min_value=0.0,
            max_value=20.0,
            value=params.get("b", 2.0),
            step=0.5,
        )
        params = {"beta": beta, "R": R, "c": c, "b": b}

    elif groove_type == "X-Naht (Doppel-V)":
        col1, col2 = st.columns(2)
        with col1:
            alpha_1 = st.number_input(
                "Winkel oben α₁ (°):",
                min_value=10.0,
                max_value=90.0,
                value=params.get("alpha_1", 50.0),
                step=1.0,
                help="Öffnungswinkel der oberen V-Naht",
            )
        with col2:
            alpha_2 = st.number_input(
                "Winkel unten α₂ (°):",
                min_value=10.0,
                max_value=90.0,
                value=params.get("alpha_2", 60.0),
                step=1.0,
                help="Öffnungswinkel der unteren V-Naht",
            )
        c = st.number_input(
            "Steg c (mm):",
            min_value=0.0,
            max_value=10.0,
            value=params.get("c", 2.0),
            step=0.5,
            help="Höhe des Stegs in der Mitte",
        )
        b = st.number_input(
            "Spalt b (mm):",
            min_value=0.0,
            max_value=20.0,
            value=params.get("b", 2.0),
            step=0.5,
        )
        params = {"alpha_1": alpha_1, "alpha_2": alpha_2, "c": c, "b": b}

    elif groove_type == "HU-Naht":
        beta = st.number_input("Flankenwinkel beta (deg):", min_value=0.0, max_value=45.0, value=params.get("beta", 8.0), step=1.0)
        R = st.number_input("Radius R (mm):", min_value=1.0, max_value=30.0, value=params.get("R", 6.0), step=0.5)
        c = st.number_input("Steg c (mm):", min_value=0.0, max_value=10.0, value=params.get("c", 1.0), step=0.5)
        b = st.number_input("Spalt b (mm):", min_value=0.0, max_value=20.0, value=params.get("b", 2.0), step=0.5)
        params = {"beta": beta, "R": R, "c": c, "b": b}

    elif groove_type == "VV-Naht (V + HV)":
        col1, col2 = st.columns(2)
        with col1:
            alpha = st.number_input("Nutwinkel alpha (deg):", min_value=10.0, max_value=90.0, value=params.get("alpha", 60.0), step=1.0)
        with col2:
            beta = st.number_input("Flankenwinkel beta (deg):", min_value=5.0, max_value=90.0, value=params.get("beta", 10.0), step=1.0)
        h = st.number_input("Tiefe h (mm):", min_value=0.5, max_value=50.0, value=params.get("h", 4.0), step=0.5, help="Tiefe des V-Anteils")
        c = st.number_input("Steg c (mm):", min_value=0.0, max_value=10.0, value=params.get("c", 1.0), step=0.5)
        b = st.number_input("Spalt b (mm):", min_value=0.0, max_value=20.0, value=params.get("b", 2.0), step=0.5)
        params = {"alpha": alpha, "beta": beta, "h": h, "c": c, "b": b}

    elif groove_type == "UV-Naht (U + HV)":
        col1, col2 = st.columns(2)
        with col1:
            alpha = st.number_input("Nutwinkel alpha (deg):", min_value=10.0, max_value=90.0, value=params.get("alpha", 60.0), step=1.0)
        with col2:
            beta = st.number_input("Flankenwinkel beta (deg):", min_value=0.0, max_value=45.0, value=params.get("beta", 8.0), step=1.0)
        R = st.number_input("Radius R (mm):", min_value=1.0, max_value=30.0, value=params.get("R", 6.0), step=0.5)
        h = st.number_input("Tiefe h (mm):", min_value=0.5, max_value=50.0, value=params.get("h", 4.0), step=0.5, help="Tiefe des U-Anteils")
        b = st.number_input("Spalt b (mm):", min_value=0.0, max_value=20.0, value=params.get("b", 2.0), step=0.5)
        params = {"alpha": alpha, "beta": beta, "R": R, "h": h, "b": b}

    elif groove_type == "Doppel-HV-Naht":
        col1, col2 = st.columns(2)
        with col1:
            beta_1 = st.number_input("Winkel oben beta_1 (deg):", min_value=5.0, max_value=90.0, value=params.get("beta_1", 50.0), step=1.0)
        with col2:
            beta_2 = st.number_input("Winkel unten beta_2 (deg):", min_value=5.0, max_value=90.0, value=params.get("beta_2", 60.0), step=1.0)
        col3, col4 = st.columns(2)
        with col3:
            h1 = st.number_input("Tiefe oben h1 (mm):", min_value=0.0, max_value=50.0, value=params.get("h1", 0.0), step=0.5, help="0 = automatisch")
        with col4:
            h2 = st.number_input("Tiefe unten h2 (mm):", min_value=0.0, max_value=50.0, value=params.get("h2", 0.0), step=0.5, help="0 = automatisch")
        c = st.number_input("Steg c (mm):", min_value=0.0, max_value=10.0, value=params.get("c", 2.0), step=0.5)
        b = st.number_input("Spalt b (mm):", min_value=0.0, max_value=20.0, value=params.get("b", 2.0), step=0.5)
        params = {"beta_1": beta_1, "beta_2": beta_2, "h1": h1, "h2": h2, "c": c, "b": b}

    elif groove_type == "Doppel-U-Naht":
        col1, col2 = st.columns(2)
        with col1:
            beta_1 = st.number_input("Winkel oben beta_1 (deg):", min_value=0.0, max_value=45.0, value=params.get("beta_1", 8.0), step=1.0)
        with col2:
            beta_2 = st.number_input("Winkel unten beta_2 (deg):", min_value=0.0, max_value=45.0, value=params.get("beta_2", 10.0), step=1.0)
        col3, col4 = st.columns(2)
        with col3:
            R = st.number_input("Radius oben R (mm):", min_value=1.0, max_value=30.0, value=params.get("R", 6.0), step=0.5)
        with col4:
            R2 = st.number_input("Radius unten R2 (mm):", min_value=1.0, max_value=30.0, value=params.get("R2", 6.0), step=0.5)
        col5, col6 = st.columns(2)
        with col5:
            h1 = st.number_input("Tiefe oben h1 (mm):", min_value=0.0, max_value=50.0, value=params.get("h1", 0.0), step=0.5, help="0 = automatisch")
        with col6:
            h2 = st.number_input("Tiefe unten h2 (mm):", min_value=0.0, max_value=50.0, value=params.get("h2", 0.0), step=0.5, help="0 = automatisch")
        c = st.number_input("Steg c (mm):", min_value=0.0, max_value=10.0, value=params.get("c", 2.0), step=0.5)
        b = st.number_input("Spalt b (mm):", min_value=0.0, max_value=20.0, value=params.get("b", 2.0), step=0.5)
        params = {"beta_1": beta_1, "beta_2": beta_2, "R": R, "R2": R2, "h1": h1, "h2": h2, "c": c, "b": b}

    elif groove_type == "Doppel-HU-Naht":
        col1, col2 = st.columns(2)
        with col1:
            beta_1 = st.number_input("Winkel oben beta_1 (deg):", min_value=0.0, max_value=45.0, value=params.get("beta_1", 8.0), step=1.0)
        with col2:
            beta_2 = st.number_input("Winkel unten beta_2 (deg):", min_value=0.0, max_value=45.0, value=params.get("beta_2", 10.0), step=1.0)
        col3, col4 = st.columns(2)
        with col3:
            R = st.number_input("Radius oben R (mm):", min_value=1.0, max_value=30.0, value=params.get("R", 6.0), step=0.5)
        with col4:
            R2 = st.number_input("Radius unten R2 (mm):", min_value=1.0, max_value=30.0, value=params.get("R2", 6.0), step=0.5)
        col5, col6 = st.columns(2)
        with col5:
            h1 = st.number_input("Tiefe oben h1 (mm):", min_value=0.0, max_value=50.0, value=params.get("h1", 0.0), step=0.5, help="0 = automatisch")
        with col6:
            h2 = st.number_input("Tiefe unten h2 (mm):", min_value=0.0, max_value=50.0, value=params.get("h2", 0.0), step=0.5, help="0 = automatisch")
        c = st.number_input("Steg c (mm):", min_value=0.0, max_value=10.0, value=params.get("c", 2.0), step=0.5)
        b = st.number_input("Spalt b (mm):", min_value=0.0, max_value=20.0, value=params.get("b", 2.0), step=0.5)
        params = {"beta_1": beta_1, "beta_2": beta_2, "R": R, "R2": R2, "h1": h1, "h2": h2, "c": c, "b": b}

    elif groove_type == "Bördelnaht":
        _BOERDEL_CODES = {
            "1.12 — beidseitig gebördelt": "1.12",
            "1.13 — einseitig gebördelt": "1.13",
            "2.12 — mit Spalt": "2.12",
        }
        code_label = st.selectbox("Stoßart (ISO 9692-1):", list(_BOERDEL_CODES.keys()))
        code_number = _BOERDEL_CODES[code_label]
        col1, col2 = st.columns(2)
        with col1:
            t_1 = st.number_input("Blechdicke 1 t_1 (mm):", min_value=0.5, max_value=20.0, value=params.get("t_1", 3.0), step=0.5)
        with col2:
            t_2 = st.number_input("Blechdicke 2 t_2 (mm):", min_value=0.5, max_value=20.0, value=params.get("t_2", 3.0), step=0.5)
        alpha = st.number_input("Bördelwinkel alpha (deg):", min_value=0.0, max_value=45.0, value=params.get("alpha", 12.0), step=1.0)
        b = st.number_input("Spalt b (mm):", min_value=0.0, max_value=10.0, value=params.get("b", 1.0), step=0.5)
        e = st.number_input("Überlappung e (mm):", min_value=0.0, max_value=20.0, value=params.get("e", 2.0), step=0.5)
        params = {"t_1": t_1, "t_2": t_2, "alpha": alpha, "b": b, "e": e, "code_number": code_number}

    elif groove_type == "Kehlnaht":
        _KEHL_CODES = {
            "3.1.1 — Überlappstoß (einseitig)": "3.1.1",
            "3.1.2 — T-Stoß (einseitig)": "3.1.2",
            "3.1.3 — Eckstoß (einseitig)": "3.1.3",
            "4.1.1 — Überlappstoß (beidseitig)": "4.1.1",
            "4.1.2 — T-Stoß (beidseitig)": "4.1.2",
            "4.1.3 — Eckstoß (beidseitig)": "4.1.3",
        }
        code_label = st.selectbox("Stoßart (ISO 9692-1):", list(_KEHL_CODES.keys()))
        code_number = _KEHL_CODES[code_label]
        col1, col2 = st.columns(2)
        with col1:
            t_1 = st.number_input("Blechdicke 1 t_1 (mm):", min_value=0.5, max_value=100.0, value=params.get("t_1", 5.0), step=0.5)
        with col2:
            t_2 = st.number_input("Blechdicke 2 t_2 (mm):", min_value=0.5, max_value=100.0, value=params.get("t_2", 5.0), step=0.5)
        alpha = st.number_input("Kehlnahtwinkel alpha (deg):", min_value=0.0, max_value=90.0, value=params.get("alpha", 45.0), step=1.0)
        b = st.number_input("Spalt b (mm):", min_value=0.0, max_value=10.0, value=params.get("b", 0.0), step=0.5)
        e = st.number_input("Nahtdicke e (mm):", min_value=0.0, max_value=30.0, value=params.get("e", 3.0), step=0.5, help="a-Maß der Kehlnaht")
        params = {"t_1": t_1, "t_2": t_2, "alpha": alpha, "b": b, "e": e, "code_number": code_number}

    state.groove["params"] = params

    # Try to create groove object and render preview
    groove_obj = _get_groove_object(groove_type, params)
    if groove_obj:
        st.success("✅ Nutobjekt erfolgreich erstellt")
        state.groove["object"] = groove_obj

        st.markdown("---")

        # ─── Extract profile data for both views ─────────────
        profile_data = None
        try:
            from weldx import Q_

            profile = groove_obj.to_profile(width_default=Q_(2, "mm"))

            # Collect points from each shape, rasterizing arcs for smooth curves
            shape_point_lists = []
            for shape in profile.shapes:
                pts = []
                for seg in shape.segments:
                    seg_type = type(seg).__name__
                    if seg_type == "ArcSegment":
                        raster = seg.rasterize(raster_width=Q_(0.5, "mm"))
                        arc_pts = raster.m.T
                        for pt in arc_pts[:-1]:
                            pts.append((float(pt[0]), float(pt[1])))
                    else:
                        start = seg.point_start.m
                        pts.append((float(start[0]), float(start[1])))
                last_end = shape.segments[-1].point_end.m
                pts.append((float(last_end[0]), float(last_end[1])))
                shape_point_lists.append(pts)

            # Build closed outline: left half bottom→top, right half top→bottom
            left_pts = [p for spl in shape_point_lists for p in spl if p[0] <= 0.01]
            right_pts = [p for spl in shape_point_lists for p in spl if p[0] >= -0.01]
            left_pts.sort(key=lambda p: p[1])
            right_pts.sort(key=lambda p: p[1], reverse=True)
            outline = left_pts + right_pts
            if outline and outline[0] != outline[-1]:
                outline.append(outline[0])
            profile_data = outline
        except Exception:
            pass

        # ─── Side-by-side: 2D + 3D ───────────────────────────
        col_2d, col_3d = st.columns(2)

        with col_2d:
            st.markdown("**Querschnitt (2D):**")
            try:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt

                fig, ax = plt.subplots(figsize=(5, 4))
                groove_obj.plot(ax=ax)

                ax.set_aspect("equal")
                ax.set_xlabel("Breite [mm]")
                ax.set_ylabel("Höhe [mm]")
                ax.set_title(f"{groove_type} — ISO 9692-1")
                ax.grid(True, alpha=0.3, color="#cccccc")

                fig.patch.set_facecolor("white")
                ax.set_facecolor("white")
                ax.tick_params(colors="#333333")
                ax.xaxis.label.set_color("#333333")
                ax.yaxis.label.set_color("#333333")
                ax.title.set_color("#111111")
                for spine in ax.spines.values():
                    spine.set_color("#999999")

                st.pyplot(fig)
                plt.close(fig)
            except Exception as e:
                st.warning(f"2D-Vorschau nicht möglich: {e}")

        with col_3d:
            st.markdown("**3D-Vorschau:**")
            try:
                import plotly.graph_objects as go

                if not shape_point_lists or len(shape_point_lists) < 1:
                    raise ValueError("Profil-Geometrie nicht extrahierbar")

                # Determine seam length proportional to cross-section
                all_x = [p[0] for spl in shape_point_lists for p in spl]
                all_z = [p[1] for spl in shape_point_lists for p in spl]
                seam_len = max(max(all_x) - min(all_x), max(all_z) - min(all_z)) * 3

                fig3d = go.Figure()
                plate_color = "#808080"

                # Extrude each shape (plate half) as a solid body
                for shape_pts in shape_point_lists:
                    if len(shape_pts) < 3:
                        continue

                    # Close the polygon if not already closed
                    pts = list(shape_pts)
                    if pts[0] != pts[-1]:
                        pts.append(pts[0])

                    cx = [p[0] for p in pts]
                    cz = [p[1] for p in pts]
                    n = len(cx) - 1  # number of edges

                    # Build solid extrusion mesh: front + back + side walls
                    vx, vy, vz = [], [], []
                    ti, tj, tk = [], [], []

                    # Vertices: front face (y=0) then back face (y=seam_len)
                    for p in pts[:-1]:
                        vx.append(p[0]); vy.append(0.0); vz.append(p[1])
                    for p in pts[:-1]:
                        vx.append(p[0]); vy.append(seam_len); vz.append(p[1])

                    # Front face triangulation (fan from vertex 0)
                    for i in range(1, n - 1):
                        ti.append(0); tj.append(i); tk.append(i + 1)

                    # Back face triangulation (fan from vertex n)
                    base = n
                    for i in range(1, n - 1):
                        ti.append(base); tj.append(base + i + 1); tk.append(base + i)

                    # Side walls (quad per edge, split into 2 triangles)
                    for i in range(n):
                        i_next = (i + 1) % n
                        f0, f1 = i, i_next           # front vertices
                        b0, b1 = n + i, n + i_next   # back vertices
                        ti.append(f0); tj.append(f1); tk.append(b0)
                        ti.append(f1); tj.append(b1); tk.append(b0)

                    fig3d.add_trace(go.Mesh3d(
                        x=vx, y=vy, z=vz,
                        i=ti, j=tj, k=tk,
                        color=plate_color,
                        opacity=1.0,
                        flatshading=True,
                        lighting=dict(
                            ambient=0.35,
                            diffuse=0.65,
                            specular=0.4,
                            roughness=0.5,
                            fresnel=0.3,
                        ),
                        lightposition=dict(x=200, y=200, z=400),
                        showlegend=False,
                        hoverinfo="skip",
                    ))

                    # Edge outlines for clarity
                    for y_val in [0.0, seam_len]:
                        fig3d.add_trace(go.Scatter3d(
                            x=cx, y=[y_val] * len(cx), z=cz,
                            mode="lines",
                            line=dict(color="#333333", width=2),
                            showlegend=False,
                            hoverinfo="skip",
                        ))

                fig3d.update_layout(
                    scene=dict(
                        xaxis_title="Breite [mm]",
                        yaxis_title="Nahtlänge [mm]",
                        zaxis_title="Höhe [mm]",
                        aspectmode="data",
                        bgcolor="white",
                        xaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="#f5f5f5"),
                        yaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="#f5f5f5"),
                        zaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="#f5f5f5"),
                        camera=dict(
                            eye=dict(x=1.5, y=1.5, z=0.8),
                            up=dict(x=0, y=0, z=1),
                        ),
                    ),
                    paper_bgcolor="white",
                    font=dict(color="#333333"),
                    height=420,
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                st.plotly_chart(fig3d, use_container_width=True)
            except Exception as e:
                st.info(f"3D-Vorschau nicht verfügbar: {e}")
    else:
        st.warning(
            "Nutobjekt konnte nicht erstellt werden. "
            "Stellen Sie sicher, dass **weldx** installiert ist."
        )


_PATH_X_KEYS = ("x", "pos_x", "px", "x_mm", "tcp_x")
_PATH_Y_KEYS = ("y", "pos_y", "py", "y_mm", "tcp_y")
_PATH_Z_KEYS = ("z", "pos_z", "pz", "z_mm", "tcp_z")
_PATH_TIME_KEYS = ("time", "zeit", "sec", "t_s", "tsec")
_PATH_UNIT_PRESETS = ["mm", "m", "inch"]
_UNIT_TO_MM = {"mm": 1.0, "m": 1000.0, "inch": 25.4}


def _render_path_help():
    """Info expander for the path-CSV format."""
    with st.expander("ℹ️ CSV-Format & Beispiele"):
        st.markdown(
            """
**Erwartet:** Komma-getrennte CSV mit einer Header-Zeile (UTF-8).

**Spalten**
- **X / Y / Z** (Pflicht) – Pfad-Punkte. Spalten mit Namen wie
  `x`/`y`/`z`, `pos_x`/`pos_y`/`pos_z`, `tcp_x`/… werden automatisch
  erkannt; vor dem Import lassen sich alle Spalten frei zuordnen.
- **Zeitspalte** (optional) – Zeit in **Sekunden**. Spalten wie `time`,
  `zeit`, `t_s`, `seconds` werden automatisch erkannt. Ohne Zeitspalte
  wird der Sample-Index (0, 1, 2, …) als Sekunden verwendet.
- **Position-Einheit** – Auswahl `mm` (Standard), `m`, `inch`. Werte
  werden intern in mm umgerechnet.

**Beispiel ohne Zeit (mm):**

```
x,y,z
0.0,0.0,0.0
10.5,0.0,0.0
21.0,0.0,0.0
31.5,0.0,0.0
```

**Beispiel mit Zeit (s, mm):**

```
time_s,x,y,z
0.000,0.0,0.0,0.0
0.100,10.5,0.0,0.0
0.200,21.0,0.0,0.0
0.300,31.5,0.0,0.0
```

Beim Import wird der Pfad als zeitabhängiges Koordinatensystem im CSM
unter dem gewählten Eltern-KOS abgelegt und beim Speichern in der
WelDX-Datei als `LocalCoordinateSystem` mit `time` und `coordinates`
persistiert. Im 3D-Viewer (Koordinatensysteme → Transformationen)
erscheint der Pfad automatisch als Trajektorie.
            """
        )


def _render_path_import(state):
    """File uploader + column/unit picker for path CSVs (3D welding paths)."""
    if not hasattr(state, "coordinate_systems") or state.coordinate_systems is None:
        state.coordinate_systems = {}

    st.markdown("**CSV-Pfaddaten:**")

    # ── List existing imported paths with delete button ──
    existing = {
        n: info for n, info in state.coordinate_systems.items()
        if isinstance(info, dict) and info.get("_imported_path")
    }
    if existing:
        st.write("**Importierte Pfade:**")
        for name, info in list(existing.items()):
            traj = info.get("trajectory")
            n_pts = int(traj.shape[0]) if traj is not None and hasattr(traj, "shape") else 0
            col_a, col_b = st.columns([6, 1])
            with col_a:
                st.markdown(
                    f"`{name}` — {n_pts:,} Punkte · "
                    f"Eltern-KOS: `{info.get('parent', '?')}`"
                )
            with col_b:
                if st.button("🗑️", key=f"del_path_{name}", help="Pfad entfernen"):
                    remove_imported_path(state, name)
                    st.rerun()
        st.divider()

    col_upload, col_info = st.columns([2, 1])
    with col_upload:
        uploaded = st.file_uploader(
            "CSV-Datei mit Schweißbahnkoordinaten hochladen",
            type=["csv"],
            key="path_uploader",
        )
    with col_info:
        _render_path_help()

    if uploaded is None:
        return

    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"CSV nicht lesbar: {e}")
        return

    if df.empty:
        st.error("CSV ist leer.")
        return

    cols = list(df.columns)

    def _auto(col_keys):
        for c in cols:
            if str(c).lower() in col_keys:
                return c
        return None

    # Numeric column fallbacks (skip time)
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]

    x_default = _auto(_PATH_X_KEYS)
    y_default = _auto(_PATH_Y_KEYS)
    z_default = _auto(_PATH_Z_KEYS)
    t_default = None
    for c in cols:
        if any(k in str(c).lower() for k in _PATH_TIME_KEYS):
            t_default = c
            break

    # Fallback if x/y/z not auto-detected: first three numeric columns
    leftover = [c for c in numeric_cols if c != t_default]
    if x_default is None and len(leftover) >= 1:
        x_default = leftover[0]
    if y_default is None and len(leftover) >= 2:
        y_default = leftover[1]
    if z_default is None and len(leftover) >= 3:
        z_default = leftover[2]

    with st.form("path_import_form", border=True):
        st.markdown("**Vorschau (erste 5 Zeilen):**")
        st.dataframe(df.head(), use_container_width=True)

        col_x, col_y, col_z, col_t = st.columns(4)
        with col_x:
            x_col = st.selectbox(
                "X-Spalte", cols,
                index=cols.index(x_default) if x_default in cols else 0,
            )
        with col_y:
            y_col = st.selectbox(
                "Y-Spalte", cols,
                index=cols.index(y_default) if y_default in cols else min(1, len(cols) - 1),
            )
        with col_z:
            z_col = st.selectbox(
                "Z-Spalte", cols,
                index=cols.index(z_default) if z_default in cols else min(2, len(cols) - 1),
            )
        with col_t:
            t_options = ["(keine — Sample-Index)"] + cols
            t_idx = t_options.index(t_default) if t_default in cols else 0
            time_col = st.selectbox("Zeitspalte (s)", t_options, index=t_idx)

        col_u, col_p, col_n = st.columns([1, 2, 2])
        with col_u:
            unit = st.selectbox("Einheit", _PATH_UNIT_PRESETS, index=0)
        with col_p:
            cs_options = list(state.coordinate_systems.keys())
            if not cs_options:
                cs_options = ["workpiece"]
            parent_default = "workpiece" if "workpiece" in cs_options else cs_options[0]
            parent_cs = st.selectbox(
                "Eltern-Koordinatensystem",
                options=cs_options,
                index=cs_options.index(parent_default),
            )
        with col_n:
            default_name = uploaded.name.rsplit(".", 1)[0]
            path_name = st.text_input(
                "Pfad-Name",
                value=default_name,
                help="Eindeutiger CS-Name im CSM (z. B. tcp_design_2).",
            )

        submitted = st.form_submit_button("Pfad importieren", type="primary")

    if not submitted:
        return

    try:
        x = pd.to_numeric(df[x_col], errors="coerce").to_numpy(dtype=float)
        y = pd.to_numeric(df[y_col], errors="coerce").to_numpy(dtype=float)
        z = pd.to_numeric(df[z_col], errors="coerce").to_numpy(dtype=float)
        t = None
        if time_col != "(keine — Sample-Index)":
            t = pd.to_numeric(df[time_col], errors="coerce").to_numpy(dtype=float)

        mask = ~(np.isnan(x) | np.isnan(y) | np.isnan(z))
        if t is not None:
            mask &= ~np.isnan(t)
        x, y, z = x[mask], y[mask], z[mask]
        if t is not None:
            t = t[mask]
        if x.size == 0:
            st.error("Keine numerischen Punkte gefunden.")
            return

        scale = _UNIT_TO_MM[unit]
        pts_mm = np.column_stack([x, y, z]) * scale

        info = add_imported_path(
            state,
            name=path_name.strip() or "path",
            parent_cs=parent_cs,
            points_xyz_mm=pts_mm,
            time_s=t,
        )
        st.success(
            f"Pfad '{info['name']}' importiert: {len(pts_mm):,} Punkte, "
            f"Eltern-KOS '{parent_cs}'."
        )

        _plot_path_preview(pts_mm, info["name"])
        st.rerun()
    except Exception as e:
        st.error(f"Fehler beim Importieren: {e}")


def _plot_path_preview(pts_mm: np.ndarray, name: str):
    """Small Plotly 3D preview of an imported path."""
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter3d(
            x=pts_mm[:, 0], y=pts_mm[:, 1], z=pts_mm[:, 2],
            mode="lines+markers",
            line=dict(color="#cc0000", width=4),
            marker=dict(size=2, color="#cc0000"),
            name=name,
            hoverinfo="name",
        ))
        fig.update_layout(
            scene=dict(
                xaxis_title="X [mm]", yaxis_title="Y [mm]", zaxis_title="Z [mm]",
                aspectmode="data", bgcolor="white",
                xaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="#f5f5f5"),
                yaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="#f5f5f5"),
                zaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="#f5f5f5"),
            ),
            paper_bgcolor="white", font=dict(color="#333333"),
            height=380, margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info(f"3D-Vorschau nicht verfügbar: {e}")


def _render_workpiece_geometry_tab(state):
    """Render the workpiece geometry tab."""
    st.subheader("Werkstück-Geometrie")

    # Initialize tree if not present
    if not hasattr(state, "tree") or state.tree is None:
        state.tree = {
            "seam_length": 100.0,
            "welding_speed": 500.0,
        }

    col1, col2 = st.columns(2)

    with col1:
        seam_length = st.number_input(
            "Nahtlänge (mm):",
            min_value=1.0,
            max_value=10000.0,
            value=float(state.tree.get("seam_length", 100.0)),
            step=10.0,
        )
        state.tree["seam_length"] = seam_length

    with col2:
        welding_speed = st.number_input(
            "Schweißgeschwindigkeit (mm/s):",
            min_value=0.1,
            max_value=1000.0,
            value=float(state.tree.get("welding_speed", 500.0)),
            step=10.0,
        )
        state.tree["welding_speed"] = welding_speed

    st.info(
        "**Komplexe 3D-Schweißbahnen:** Sie können komplexe 3D-Schweißpfade als "
        "CSV importieren. Sie werden als zeitabhängiges Koordinatensystem im CSM "
        "abgelegt und erscheinen automatisch als Trajektorie im 3D-Viewer."
    )

    _render_path_import(state)


def render_workpiece(state):
    """
    Main render function for the workpiece panel.

    Parameters
    ----------
    state : WeldxFileState
        The application state object with attributes:
        - state.base_metal: dict with material information
        - state.groove: dict or object with groove geometry
        - state.tree: dict with workpiece geometry parameters
    """
    st.markdown("## Werkstück-Konfiguration")

    # Create three tabs
    tab1, tab2, tab3 = st.tabs([
        "Basismaterial",
        "Nahtgeometrie (ISO 9692-1)",
        "Werkstück-Geometrie",
    ])

    with tab1:
        _render_basismaterial_tab(state)

    with tab2:
        _render_groove_tab(state)

    with tab3:
        _render_workpiece_geometry_tab(state)
