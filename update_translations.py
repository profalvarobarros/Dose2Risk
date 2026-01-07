
import os

new_translations = [
    # UI Labels
    ('Opções de Filtro e Seleção de Dados', 'Filter and Data Selection Options', 'Opciones de Filtro y Selección de Datos', 'Options de Filtre et Sélection de Données'),
    ('Mostrar campos com dose > 4 Sv (Segurança)', 'Show fields with dose > 4 Sv (Safety)', 'Mostrar campos con dosis > 4 Sv (Seguridad)', 'Afficher les champs avec dose > 4 Sv (Sécurité)'),
    ('Se desmarcado, colunas onde todos os valores excedem o limite de segurança serão suprimidas do relatório final.', 'If unchecked, columns where all values exceed the safety limit will be suppressed from the final report.', 'Si está desmarcado, las columnas donde todos los valores exceden el límite de seguridad serán suprimidas del informe final.', 'Si décoché, les colonnes où toutes les valeurs dépassent la limite de sécurité seront supprimées du rapport final.'),
    ('Sexo', 'Sex', 'Sexo', 'Sexe'),
    ('Masculino (M)', 'Male (M)', 'Masculino (M)', 'Masculin (M)'),
    ('Feminino (F)', 'Female (F)', 'Femenino (F)', 'Féminin (F)'),
    ('Resultados (Colunas)', 'Results (Columns)', 'Resultados (Columnas)', 'Résultats (Colonnes)'),
    ('ERR (Excesso de Risco Relativo)', 'ERR (Excess Relative Risk)', 'ERR (Exceso de Riesgo Relativo)', 'ERR (Excès de Risque Relatif)'),
    ('LAR (Risco Atribuível ao Longo da Vida)', 'LAR (Lifetime Attributable Risk)', 'LAR (Riesgo Atribuible a lo Largo de la Vida)', 'LAR (Risque Attribuable au Long de la Vie)'),
    ('Órgãos', 'Organs', 'Órganos', 'Organes'),
    ('Selecionar Todos', 'Select All', 'Seleccionar Todos', 'Tout Sélectionner'),
    ('Desmarcar Todos', 'Deselect All', 'Deseleccionar Todos', 'Tout Désélectionner'),
    
    # Organs
    ('red_marrow', 'Red Marrow', 'Médula Ósea Roja', 'Moelle Osseuse Rouge'),
    ('lung', 'Lung', 'Pulmón', 'Poumon'),
    ('breast', 'Breast', 'Mama', 'Sein'),
    ('thyroid', 'Thyroid', 'Tiroides', 'Thyroïde'),
    ('stomach_wall', 'Stomach Wall', 'Pared Estomacal', 'Paroi de l’Estomac'),
    ('lli_wall', 'Lower Large Intestine Wall', 'Pared Intestino Grueso Inf.', 'Paroi du Gros Intestin Inf.'),
    ('uli_wall', 'Upper Large Intestine Wall', 'Pared Intestino Grueso Sup.', 'Paroi du Gros Intestin Sup.'),
    ('si_wall', 'Small Intestine Wall', 'Pared Intestino Delgado', 'Paroi de l’Intestin Grêle'),
    ('liver', 'Liver', 'Hígado', 'Foie'),
    ('esophagus', 'Esophagus', 'Esófago', 'Œsophage'),
    ('bladder_wall', 'Bladder Wall', 'Pared de la Vejiga', 'Paroi de la Vessie'),
    ('ovaries', 'Ovaries', 'Ovarios', 'Ovaires'),
    ('uterus', 'Uterus', 'Útero', 'Utérus'),
    ('testes', 'Testes', 'Testículos', 'Testicules'),
    ('kidneys', 'Kidneys', 'Riñones', 'Reins'),
    ('pancreas', 'Pancreas', 'Páncreas', 'Pancréas'),
    ('spleen', 'Spleen', 'Bazo', 'Rate'),
    ('skin', 'Skin', 'Piel', 'Peau'),
    ('muscle', 'Muscle', 'Músculo', 'Muscle'),
    ('adrenals', 'Adrenals', 'Glándulas Suprarrenales', 'Glandes Surrénales'),
    ('brain', 'Brain', 'Cerebro', 'Cerveau'),
    ('surface_bone', 'Surface Bone', 'Superficie Ósea', 'Surface Osseuse'),
    ('thymus', 'Thymus', 'Timo', 'Thymus')
]

base_path = r'g:\Meu Drive\Doutorado - IME\Tese\DoseToRisk\Programa_Python_AR\dose2risk\api\translations'
langs = {'en': 1, 'es': 2, 'fr': 3}

for lang_code, idx in langs.items():
    po_file = os.path.join(base_path, lang_code, 'LC_MESSAGES', 'messages.po')
    
    with open(po_file, 'a', encoding='utf-8') as f:
        f.write('\n\n# UI Filters & Organs\n')
        for item in new_translations:
            msgid = item[0]
            msgstr = item[idx]
            entry = f'\nmsgid "{msgid}"\nmsgstr "{msgstr}"\n'
            f.write(entry)

print("Traduções adicionadas com sucesso.")
