        // ── Wave I3: top-level runtime i18n ────────────────────────────────
        // Lookups: RT('reading.next_question'), RT('cons.title_default'), etc.
        // Same lang resolution as the tutor widget at line ~8086 (NETS_CTX.lang
        // -> <html lang> -> 'en'). Declared OUTSIDE the tutor IIFE so every
        // phase scope (reading/consolidation/MS/AQ/WC/MM/PL/MB/RL/boss/results)
        // can read it. Adding a key? Group by phase prefix and keep all three
        // languages in sync — Russian translations follow the natural-register
        // rules per Wave I3 spec, NOT calques.
        const RUNTIME_LABELS = {
            uz: {
                // skip overlay
                'skip.label':            "⏭ Fazani o'tkazib yuborish",
                // shared button labels
                'btn.continue':          'Davom etish',
                'btn.next':              'Keyingi',
                'btn.next_page':         'Keyingi sahifa',
                'btn.next_panel':        'Keyingi panel',
                'btn.finish':            'Yakunlash',
                'btn.start':             'Boshlash',
                'btn.confirm':           'Tasdiqlash',
                'btn.check_answer':      'Javobni tekshirish',
                'btn.submit_answer':     'Javob berish',
                'btn.next_question':     'Keyingi savol',
                'btn.next_stage':        'Keyingi bosqich',
                'btn.next_game':         "Keyingi o'yin",
                'btn.next_chain':        'Keyingi zanjir',
                'btn.next_box':          'Keyingi quti',
                'btn.complete':          'Tugatish',
                'btn.retry':             'Qayta urinish',
                'btn.game_break':        "O'yin tanaffusi",
                'btn.read':              "O'qishga o'tish",
                'btn.submit_response':   'Javobni yuborish',
                'btn.send':              "Javobni Jo'natish",
                'btn.show_hint':         "💡 Hint ko'rish",
                'btn.hide_hint':         "💡 Hintni yopish",
                'btn.ask_tutor':         '💬 Tyutor',
                'rl.ai_unavailable_wrong': 'Javob qabul qilindi. AI hozirda javob bera olmadi.',
                // verdicts (shared)
                'verdict.correct':       "✓ To'g'ri!",
                'verdict.wrong':         "✗ Noto'g'ri.",
                'verdict.right_answer':  "To'g'ri javob:",
                // reading
                'reading.title_default': "O'qish",
                'reading.placeholder':   'Javobingizni yozing...',
                'reading.check':         'Tekshirish',
                'reading.next_question': 'Keyingi savol',
                'reading.page_label':    'Sahifa',
                'reading.must_answer':   'Davom etish uchun savolga javob bering.',
                'reading.all_done':      'Reading checkpoint bajarildi. Endi davom etishingiz mumkin.',
                'reading.correct':       "✓ To'g'ri!",
                'reading.wrong':         "✗ Noto'g'ri.",
                'reading.right_answer':  "To'g'ri javob:",
                'reading.ai_correct_default': "To'g'ri!",
                // consolidation
                'cons.title_default':    'Mustahkamlash',
                'cons.expected_prefix':  'Kutilayotgan javob: ',
                'cons.show_answer':      "Javobni ko'rsatish",
                // memory sprint
                'ms.question_prefix':    'Savol',
                'ms.score_great':        'Ajoyib. Xotira sprint ritmini ushladingiz va asosiy terminlarni tez esladingiz.',
                'ms.score_meh':          "Hali emas. Lekin sprint ishladi, endi qaysi joylar qayta ko'rishni talab qilishini bilasiz.",
                // adaptive quiz
                'aq.question_of':        'Savol',
                'aq.upload_solution':    'Yechimni yuklang (📷)',
                'aq.solution_uploaded':  '📷 Sizning yechimingiz yuklandi',
                'aq.upload_first':       'Avval yechimingizni yuklang!',
                'aq.correct_prefix':     "To'g'ri! ",
                'aq.wrong_prefix':       "Noto'g'ri. To'g'ri javob: ",
                // adaptive quiz — Apple-glass redesign labels (2026-05-01)
                'aq.tier_easy':          'Oson',
                'aq.tier_medium':        "O'rtacha",
                'aq.tier_hard':          'Qiyin',
                'aq.answer_label':       'Javob',
                'aq.answer_help':        'Yakuniy javobingizni yozing.',
                'aq.status_step1':       '1-qadam',
                'aq.status_upload_done': 'Yuklandi',
                'aq.status_correct':     "To'g'ri",
                'aq.status_review':      "Ko'rib chiqing",
                'aq.upload_drop_label':  'Yechimingizni tasdiqlang',
                'aq.upload_subtitle':    'Javobingiz saqlandi. Yechim daftarini biriktiring.',
                // why-chain (sentence fill)
                'wc.chain_label':        'Zanjir',
                'wc.level_label':        'Daraja',
                'wc.checking':           'Tekshirilmoqda…',
                'wc.right_answer':       "To'g'ri javob: ",
                // tile match
                'tm.pairs_status':       'Juftlarni toping:',
                'tm.eyebrow':            "O'YIN 3 · MATCH",
                'tm.title':              "Tushuncha va ma'noni mos qiling",
                'tm.subtitle':           "Chapdan bitta plitkani, so'ng o'ngdan unga mos keluvchini tanlang. To'g'ri juftliklar yo'qoladi, noto'g'rilari titraydi.",
                'tm.col_left':           'Tushuncha',
                'tm.col_right':          "Ma'no",
                'tm.stats_matched':      'Topildi',
                'tm.stats_wrong':        'Xato',
                'tm.toast_correct':      "To'g'ri! +100 XP.",
                'tm.toast_streak':       '3 ta ketma-ket! +50 XP',
                'tm.toast_wrong':        'Mos kelmadi.',
                'tm.toast_pick_left':    "Avval chap plitkadan tanlang.",
                'tm.toast_perfect_clear': "Mukammal! Birorta xato yo'q.",
                'tm.result_perfect':     'Mukammal!',
                'tm.result_flawless':    'Deyarli mukammal',
                'tm.result_cleared':     'Tugadi',
                'tm.result_not_yet':     'Hali emas',
                'tm.result_body_perfect': "Bitta ham xato yo'q. Eslab qoling — bu sizning kuchingiz.",
                'tm.result_body_flawless': 'Faqat bitta xato. Yaxshi natija.',
                'tm.result_body_cleared': 'Barcha juftlar topildi.',
                'tm.result_body_partial': "Vaqt tugadi. Qaytadan urinib ko'ring.",
                'tm.dock_select':        'Juftlikni tanlang',
                'tm.dock_choose_meaning': "Ma'noni tanlang",
                'tm.dock_next_game':     "Keyingi o'yin",
                'tm.dock_replay':        "Qayta o'ynash",
                'tm.hint_correct':       "To'g'ri: ",
                'tm.xp_label':           'Tile Match XP',
                // puzzle lock
                'pl.fit_status':         'Mos joyga:',
                'pl.no_question':        '(savol berilmagan)',
                'pl.step_status':        'Qadam {n} / {total}',
                'pl.step_locked':        'Avval oldingi qadamni hal qiling',
                'pl.wrong_feedback':     "Notog'ri javob — qaytadan urinib ko'ring.",
                // mystery box
                'mb.boxes_status':       'Qutilar:',
                'mb.right_category':     "To'g'ri toifa!",
                'mb.actually_prefix':    'Aslida bu — ',
                'mb.outcome_correct':    "To'g'ri javob — toifa va yechim mos!",
                'mb.outcome_part_ans':   "Yechim to'g'ri, lekin toifa noto'g'ri edi.",
                'mb.outcome_part_cat':   "Toifa to'g'ri, lekin yechim noto'g'ri. Aslida: ",
                'mb.outcome_wrong':      "Yechim ham, toifa ham noto'g'ri. Aslida: ",
                // real-life
                'rl.task_badge':         'VAZIFA',
                'rl.question_of':        'Savol',
                'rl.textarea_placeholder': 'Tahlil yozing (kamida 20 belgi)...',
                'rl.upload_solution':    '📷 Yechimni yuklash',
                'rl.solution_uploaded':  '✓ Yechimingiz yuklandi',
                'rl.upload_required':    '📷 Iltimos, yechimingiz rasmini ham yuklang.',
                'rl.enter_answer':       'Javob kiriting.',
                'rl.correct_prefix':     "✓ To'g'ri! ",
                'rl.fill_all_fields':    "Barcha maydonlarni to'ldiring.",
                'rl.all_correct':        "✓ Barcha maydonlar to'g'ri!",
                'rl.field_hint':         "💡 Bir yoki bir nechta maydon noto'g'ri. Qayta tekshiring.",
                'rl.right_answers':      "✗ To'g'ri javoblar: ",
                'rl.min_chars':          'Iltimos, kamida 20 belgili tahlil yozing.',
                'rl.analysis_received':  '✓ Tahlilingiz qabul qilindi. AI baho beryapti...',
                'rl.ai_analyzing':       '✗ AI tahlil qilmoqda...',
                'rl.correct_count':      "To'g'ri javoblar:",
                'rl.uploaded_count':     'Yuklangan yechimlar:',
                // boss
                'boss.question_of':      'Savol',
                'boss.correct_hp':       "✓ To'g'ri! −",
                'boss.combo_hp':         '🔥 COMBO ×2! −',
                'boss.wrong_ai':         "✗ Noto'g'ri. AI tahlil qilmoqda...",
                'boss.checking':         "Tekshirilmoqda…",
                'boss.wrong_next':       "✗ Noto'g'ri. Keyingi savolga o'ting.",
                'boss.combo_x2':         '🔥 Combo ×2!',
                'boss.combo_streak':     'ketma-ket',
                'boss.victory_correct':  "To'g'ri:",
                'boss.victory_hints':    'Maslahat:',
                'boss.victory_hints_unit': 'ta',
                'boss.victory_damage':   'Boss zarari:',
                'boss.victory_finish':   '§22 Yakunlash',
                'boss.defeat_hp':        'Boss qolgan HP:',
                'boss.defeat_correct':   "To'g'ri:",
                'boss.defeat_tip':       "Zaif savollarni qayta ko'rib chiqing va qayta urinib ko'ring.",
                // FB redesign (Final Boss runtime polish) — additive keys.
                'boss.attempt_of':              'Urinish {n}/{max}',
                'boss.full_damage':             "To'liq zarba",
                'boss.half_damage':             'Yarim zarba',
                'boss.no_damage':               "Zarba yo'q",
                'boss.combo_x2_activated':      '🔥 Combo ×2 yondi!',
                'boss.low_hp_warning':          'Boss zaiflashdi — yakuniy zarba!',
                'boss.outcome.expert':          'Mutaxassis darajasi',
                'boss.outcome.strong':          'Kuchli mahorat',
                'boss.outcome.passing':         "O'tdingiz",
                'boss.outcome.hali_emas':       'Hali emas',
                'boss.stars.1':                 "1 yulduz — ortda qoldi, lekin o'tdingiz",
                'boss.stars.2':                 "2 yulduz — yaxshi mahorat",
                'boss.stars.3':                 "3 yulduz — Ajoyib mahorat!",
                'boss.hint_used_amber':         "💡 Maslahat ishlatildi · +{n} HP boss'ga",
                'boss.toast.wrong':             "Noto'g'ri — qayta urinib ko'ring",
                'boss.toast.try_again':         "Qayta urinish",
                'boss.result.xp':               '+{n} XP',
                'boss.result.summary':          "{correct}/{total} to'g'ri · {damage} HP zarar · {hints} maslahat",
                // results
                'res.headline_prefix':   'Sizning umumiy natijangiz:',
                'res.correct_suffix':    "to'g'ri",
                'res.phase_done':        'Tamomlandi',
                'res.phase_undone':      'Bajarilmadi',
                'res.amr_title':         "AMR · 2-eksa tahlili",
                'res.amr_title_short':   'AMR — 2-eksa rubrika',
                'res.amr_no_ai':         "Bu sessiyada hech qaysi javob AI tomonidan baholanmadi (faqat yopiq-format savollar bo'ldi). Ochiq javoblar (Sentence Fill, Real-Life Q5, Boss Q3-Q5) AI orqali 2-eksa bo'yicha baholanadi.",
                'res.amr_axis1':         "1-eksa · Konseptni nomlash",
                'res.amr_axis2':         "2-eksa · Bosqichlar izchilligi",
                'res.amr_no_items':      'AI tomonidan baholanmagan',
                // LMR v2 — language subjects (English / Ona Tili / Rus Tili).
                'res.lmr_title':         'LMR · 2-eksa tahlili',
                'res.lmr_title_short':   'LMR — 2-eksa rubrika',
                'res.lmr_axis1':         "1-eksa · Grammatika to'g'riligi",
                'res.lmr_axis2':         "2-eksa · So'z tanlash sifati",
                'res.tip_mastered':      "Ajoyib! Siz ushbu mavzuni mukammal o'zlashtirdingiz. Mastery promotion windowga 1 ball qo'shildi (3 dan).",
                'res.tip_proficient':    'Yaxshi. Siz mustaqil ishlay olasiz. Yana 1-2 sessiya — Mastered darajasiga yetasiz.',
                'res.tip_apprentice':    "Haqida o'ylash kerak. Konseptni nomlash yoki bosqichlarni ko'rsatishda bo'shliqlar bor — keyingi mashqlarda jarayonni yozma ko'rsating.",
                'res.tip_novice':        "Mavzuni qaytadan ko'rib chiqing. Hint Ladder va Flash Card'larni qayta o'qing, so'ng yana urinib ko'ring.",
                'res.closed_format':     "Yopiq-format javoblar tahlilingiz: ",
                'res.closing':           'Hisobot saqlandi. Keyingi takrorlash 1 kun ichida.',
                // misc
                'gb.break_done':         "O'yin tanaffusi tugadi!",
                // phase announcement card labels (Bug #4)
                'phase.game_breaks':     "O'yin tanaffusi",
                'phase.real_life':       "Hayotiy mashq",
                'phase.consolidation':   "Mustahkamlash",
                'phase.reflection':      "Mulohaza",
                // sub-game announcement labels (Bug #4)
                'game.aq':               "Moslashuvchan test",
                'game.wc':               "Gap to'ldirish",
                'game.mm':               "Juftlik topish",
                'game.tm':               'Tile Match',
                'game.pl':               "Qulf ochish",
                'game.mb':               "Sirli quti",
                'game.ttt':              "Krestiki-Nolikar",
                'game.sf':               "Gap to'ldirish",
                // Sentence Fill (sf.*) — new Stage-5 game (panel: gb-panel-sf)
                'sf.title':              "Gap to'ldirish",
                'sf.eyebrow':            "O'yin · Cloze",
                'sf.passage_label':      'Matn',
                'sf.mode_word_bank':     "So'z banki",
                'sf.mode_free_recall':   'Esdan yozish',
                'sf.subtitle_bank':      "Joyni tanlang, so'ng so'zni tanlang.",
                'sf.subtitle_recall':    "Har bir so'zni eslab yozing.",
                'sf.btn_check':          'Tekshirish',
                'sf.btn_next':           'Keyingi savol',
                'sf.result_perfect':     'Mukammal',
                'sf.result_partial':     'Hali emas',
                'sf.toast_perfect':      'Mukammal! Bonus XP.',
                'sf.toast_partial':      "Tekshirildi. To'g'ri javoblar ko'rsatildi.",
                'sf.toast_locked':       'Bu joy yopildi.',
                'sf.score_label':        'Sentence Fill XP',
                'sf.first_attempt_bonus':'+25 (birinchi urinish)',
                'sf.perfect_fill_bonus': '+100 mukammal',
                'sf.keyboard_hint':      "Tugmalar: Tab — joy/so'z · Enter — tekshirish · Backspace — tozalash",
                'sf.chain_label':        'Zanjir',
                // real-life challenge (RLC) — new 5-step flow
                'rlc.eyebrow':           'REAL-LIFE CHALLENGE',
                'rlc.title':             'Vaziyatni hal qiling',
                'rlc.subtitle':          "Mutaxassis sifatida tanlov qiling, tahlil yozing.",
                'rlc.step.decision':     '1-bosqich · Tanlov',
                'rlc.step.info':         "2-bosqich · Ma'lumot so'rash",
                'rlc.step.final':        '3-bosqich · Yakuniy tanlov',
                'rlc.step.concept':      '4-bosqich · Tushuncha',
                'rlc.step.reasoning':    '5-bosqich · Tahlil',
                'rlc.dock.continue':     'Davom etish',
                'rlc.dock.submit':       'Tasdiqlash',
                'rlc.dock.next':         'Keyingi qadam',
                'rlc.dock.finish':       'Yakunlash',
                'rlc.outcome.expert_decision': "Mutaxassis qarori \u2014 a'lo!",
                'rlc.outcome.strong_analysis': 'Kuchli tahlil',
                'rlc.outcome.passing':         "O'tdi",
                'rlc.outcome.hali_emas':       'Hali emas',
                'rlc.toast.correct':     "Zo'r! Davom etamiz.",
                'rlc.toast.wrong':       "Mos emas. Qayta o'ylab ko'ring.",
                'rlc.toast.try_again':   "Qayta urinib ko'ring.",
                'rlc.toast.locked':      "Bu qadam yopildi. To'g'ri javob ko'rsatildi.",
                'rlc.role.fire_inspector':       'Yong\u02bcin xavfsizligi nazoratchisi',
                'rlc.role.structural_engineer':  'Konstruktor muhandis',
                'rlc.role.business_consultant':  'Biznes maslahatchi',
                'rlc.role.medical_diagnostician':'Tibbiy diagnostik',
                'rlc.role.agronomist':           'Agronom',
                'rlc.role.teacher':              "O'qituvchi",
                'rlc.role.lawyer':               'Yurist',
                'rlc.role.city_planner':         'Shaharsozlik mutaxassisi',
                'rlc.role.epidemiologist':       'Epidemiolog',
                'rlc.role.ethicist':             'Etika mutaxassisi',
                'rlc.role.historian':            'Tarixchi',
                'rlc.role.general':              'Mutaxassis',
                'rlc.placeholder.reasoning': 'Fikringizni asoslang... (kamida belgilangan miqdorda)',
                'rlc.charcount':         '{n}/{min}',
                'rlc.consequence_reveal': 'Oqibat:',
                'rlc.correct_was':       "To'g'ri javob:",
                // tic tac toe (Apple-glass redesign)
                'ttt.heroEyebrow':       'Talaba va AI',
                'ttt.heroTitle':         "Bilimingiz taxtani boshqaradi.",
                'ttt.subtitle':          "Avval xohlagan hujayrangizni bosing. To'g'ri javob X ni shu joyga qo'yadi. Noto'g'ri javob — boshqa bo'sh hujayraga uchadi.",
                'ttt.draws':             'Duranglar',
                'ttt.losses':            "Mag'lubiyat",
                'ttt.correct':           "To'g'ri",
                'ttt.boardTitle':        'Taktik taxta',
                'ttt.boardCopy':         "AI bilan o'ynash uchun hujayrani tanlang.",
                'ttt.boardCopyAnswer':   "To'g'ri javob — belgi siz tanlagan joyga tushadi. Noto'g'ri — tasodifiy joyga.",
                'ttt.boardCopyAI':       "AI optimal o'ynaydi. Eng yaxshi natija — durang.",
                'ttt.turnYour':          'Sizning yurishingiz',
                'ttt.turnAI':            "AI o'ylamoqda",
                'ttt.turnAnswer':        'Avval javob bering',
                'ttt.stageLabel':        'Hujayrani egallash uchun javob',
                'ttt.feedbackCorrect':   "To'g'ri. X siz tanlagan joyga tushdi. +50 XP.",
                'ttt.feedbackWrong':     "Noto'g'ri. X tasodifiy bo'sh hujayraga uchdi.",
                'ttt.feedbackMercy':     "Noto'g'ri, lekin omadli sakrash. X siz tanlagan joyga qoldi.",
                'ttt.resultWinTitle':    "Imkonsiz yuz berdi",
                'ttt.resultWinText':     "Optimal AI ni yengdingiz. Standart rejimda bu deyarli imkonsiz.",
                'ttt.resultDrawTitle':   "Chiziqni tutdingiz",
                'ttt.resultDrawText':    "Durang qayd etildi. Optimal AI ga qarshi bu eng yaxshi haqiqiy natija.",
                'ttt.resultLossTitle':   'Hali emas',
                'ttt.resultLossText':    "AI yutdi. Bu sharm emas — diagnostika. Noto'g'ri javoblar nazoratni qaytib oladi.",
                'ttt.sessionStrongTitle': "Kuchli sessiya",
                'ttt.sessionStrongText': "2+ durang. Taktik bonus qo'shildi.",
                'ttt.sessionSolidTitle': "Mustahkam sessiya",
                'ttt.sessionSolidText':  "Bitta durang va to'g'ri javoblardan davomiy XP. Taxta nazoratini sayqallashda davom eting.",
                'ttt.sessionFailedTitle': "Vazifa bajarilmadi",
                'ttt.sessionFailedText': "0 durang. Mashqlarni qayta ko'rib chiqish kerak.",
                'ttt.sessionXP':         'Sessiya XP',
                'ttt.dockTap':           'Hujayrani bosing',
                'ttt.dockAnswer':        'Savolga javob bering',
                'ttt.dockNext':          "Keyingi o'yin",
                'ttt.dockResult':        'Sessiya natijasi',
                'ttt.dockComplete':      'Sessiya tugadi',
                'ttt.duolingoToast':     "Mashqlarni takrorlash kerak — qisqa mashqlardan boshlaymiz.",
                // Memory Palace (mp.*) — 4-step Method of Loci flow, panel: gb-panel-mp
                'game.mp':               "Xotira saroyi",
                'mp.heroKicker':         "Loci usuli",
                'mp.heroTitleStep1':     "Aqliy yo'l quring.",
                'mp.heroTitleStep2':     "Tushunchani joyga bog'lang.",
                'mp.heroTitleStep3':     "Saroy bo'ylab yuring.",
                'mp.heroTitleStep4':     "Xotirangizdan qaytaring.",
                'mp.heroSubStep1':       "Mavzuga mos saroyni tanlang — har joy darsning bir qismiga mos kelsin.",
                'mp.heroSubStep2':       "Har bir tushunchani jonli, kuchli tasvir bilan joylashtiring.",
                'mp.heroSubStep3':       "Saroyingiz bo'ylab tartibli yuring. Har joy-tushuncha bog'ini mustahkamlang.",
                'mp.heroSubStep4':       "Joy ishorasidan eslab javob bering. Kuchli fazoviy bog' — yengil eslash.",
                'mp.step1Label':         "1-bosqich · Saroy tanlash",
                'mp.step2Label':         "2-bosqich · Tushuncha joylashtirish",
                'mp.step3Label':         "3-bosqich · Aqliy sayr",
                'mp.step4Label':         "4-bosqich · Eslash sinovi",
                'mp.placementOccupied':  "Saqlanmoqda: {term}",
                'mp.conceptCounter':     "Tushuncha {n}/{total}",
                'mp.walkCounter':        "Bekat {n}/{total}",
                'mp.recallCounter':      "Savol {n}/{total}",
                'mp.recallQuestion':     "Bu joyga qaysi tushunchani bog'lagansiz?",
                'mp.feedbackCorrect':    "To'g'ri. Joy-tushuncha bog'i mustahkam.",
                'mp.feedbackWrong':      "Hali emas. Bu bog'ni qayta sayr qilamiz.",
                'mp.outcome.perfect':    "Ajoyib!",
                'mp.outcome.yaxshi':     "Yaxshi!",
                'mp.outcome.hali_emas_partial': "Hali emas",
                'mp.outcome.hali_emas_fail':    "Hali emas",
                'mp.level.apprentice':   "Shogird",
                'mp.level.proficient':   "Bilimdon",
                'mp.level.mastered':     "Ustoz",
                'mp.level.pending':      "Boshlovchi",
                'mp.accuracyLabel':      "Aniqlik",
                'mp.speedLabel':         "Eslash tezligi",
                'mp.levelLabel':         "Daraja",
                'mp.xpLabel':            "Sessiya XP",
                'mp.dockChoosePalace':   "Saroyni tanlang",
                'mp.dockPlaceConcept':   "Tushunchani joylashtiring",
                'mp.dockStartWalk':      "Sayrni boshlash",
                'mp.dockNextStop':       "Keyingi joy",
                'mp.dockAnswerRecall':   "Eslab javob bering",
                'mp.dockComplete':       "Saroy tugatildi",
                'mp.dockRetry':          "Qayta urinish",
                'mp.toastNetwork':       "Tarmoqda muammo. Mahalliy natija ko'rsatilmoqda.",
            },
            ru: {
                'skip.label':            '⏭ Пропустить фазу',
                'btn.continue':          'Продолжить',
                'btn.next':              'Дальше',
                'btn.next_page':         'Следующая страница',
                'btn.next_panel':        'Следующая панель',
                'btn.finish':            'Завершить',
                'btn.start':             'Начать',
                'btn.confirm':           'Подтвердить',
                'btn.check_answer':      'Проверить ответ',
                'btn.submit_answer':     'Ответить',
                'btn.next_question':     'Следующий вопрос',
                'btn.next_stage':        'Следующий этап',
                'btn.next_game':         'Следующая игра',
                'btn.next_chain':        'Следующая цепочка',
                'btn.next_box':          'Следующая коробка',
                'btn.complete':          'Завершить',
                'btn.retry':             'Попробовать снова',
                'btn.game_break':        'Игровой перерыв',
                'btn.read':              'К чтению',
                'btn.submit_response':   'Отправить ответ',
                'btn.send':              'Отправить ответ',
                'btn.show_hint':         '💡 Показать подсказку',
                'btn.hide_hint':         '💡 Скрыть подсказку',
                'btn.ask_tutor':         '💬 Тьютор',
                'rl.ai_unavailable_wrong': 'Ответ принят. AI временно недоступен.',
                'verdict.correct':       '✓ Верно!',
                'verdict.wrong':         '✗ Неверно.',
                'verdict.right_answer':  'Правильный ответ:',
                'reading.title_default': 'Чтение',
                'reading.placeholder':   'Введите ваш ответ...',
                'reading.check':         'Проверить',
                'reading.next_question': 'Следующий вопрос',
                'reading.page_label':    'Page',
                'reading.must_answer':   'Answer the checkpoint to continue.',
                'reading.all_done':      'Reading checkpoint complete. You can continue.',
                'reading.correct':       '✓ Верно!',
                'reading.wrong':         '✗ Неверно.',
                'reading.right_answer':  'Правильный ответ:',
                'reading.ai_correct_default': 'Верно!',
                'cons.title_default':    'Закрепление',
                'cons.expected_prefix':  'Ожидаемый ответ: ',
                'cons.show_answer':      'Показать ответ',
                'ms.question_prefix':    'Вопрос',
                'ms.score_great':        'Отлично. Вы поймали ритм спринта и быстро вспомнили ключевые термины.',
                'ms.score_meh':          'Пока нет. Но спринт сработал — теперь вы знаете, какие места нужно повторить.',
                'aq.question_of':        'Вопрос',
                'aq.upload_solution':    'Загрузите решение (📷)',
                'aq.solution_uploaded':  '📷 Ваше решение загружено',
                'aq.upload_first':       'Сначала загрузите решение!',
                'aq.correct_prefix':     'Верно! ',
                'aq.wrong_prefix':       'Неверно. Правильный ответ: ',
                // adaptive quiz — Apple-glass redesign labels (2026-05-01)
                'aq.tier_easy':          'Лёгкий',
                'aq.tier_medium':        'Средний',
                'aq.tier_hard':          'Сложный',
                'aq.answer_label':       'Ответ',
                'aq.answer_help':        'Запишите окончательный ответ.',
                'aq.status_step1':       'Шаг 1',
                'aq.status_upload_done': 'Загружено',
                'aq.status_correct':     'Верно',
                'aq.status_review':      'Проверьте',
                'aq.upload_drop_label':  'Подтвердите решение',
                'aq.upload_subtitle':    'Ответ сохранён. Прикрепите тетрадь с решением.',
                'wc.chain_label':        'Цепочка',
                'wc.level_label':        'Уровень',
                'wc.checking':           'Проверяем…',
                'wc.right_answer':       'Правильный ответ: ',
                'tm.pairs_status':       'Найдите пары:',
                'tm.eyebrow':            'ИГРА 3 · MATCH',
                'tm.title':              'Сопоставьте понятие и значение',
                'tm.subtitle':           'Выберите плитку слева, затем ту, что подходит ей справа. Верные пары исчезают, неверные мягко вздрагивают.',
                'tm.col_left':           'Понятие',
                'tm.col_right':          'Значение',
                'tm.stats_matched':      'Совпало',
                'tm.stats_wrong':        'Ошибки',
                'tm.toast_correct':      'Верно! +100 XP.',
                'tm.toast_streak':       '3 подряд! +50 XP',
                'tm.toast_wrong':        'Не совпало.',
                'tm.toast_pick_left':    'Сначала выберите плитку слева.',
                'tm.toast_perfect_clear': 'Идеально! Без ошибок.',
                'tm.result_perfect':     'Идеально!',
                'tm.result_flawless':    'Почти идеально',
                'tm.result_cleared':     'Готово',
                'tm.result_not_yet':     'Ещё нет',
                'tm.result_body_perfect': 'Ни одной ошибки. Запомните — это ваша сила.',
                'tm.result_body_flawless': 'Всего одна ошибка. Хороший результат.',
                'tm.result_body_cleared': 'Все пары собраны.',
                'tm.result_body_partial': 'Время вышло. Попробуйте снова.',
                'tm.dock_select':        'Выберите пару',
                'tm.dock_choose_meaning': 'Выберите значение',
                'tm.dock_next_game':     'Следующая игра',
                'tm.dock_replay':        'Сыграть заново',
                'tm.hint_correct':       'Верно: ',
                'tm.xp_label':           'Tile Match XP',
                'pl.fit_status':         'На своих местах:',
                'pl.no_question':        '(вопрос не задан)',
                'pl.step_status':        'Шаг {n} / {total}',
                'pl.step_locked':        'Сначала решите предыдущий шаг',
                'pl.wrong_feedback':     'Неверно — попробуйте ещё раз.',
                'mb.boxes_status':       'Коробки:',
                'mb.right_category':     'Категория верна!',
                'mb.actually_prefix':    'На самом деле — ',
                'mb.outcome_correct':    'Верно — категория и решение совпадают!',
                'mb.outcome_part_ans':   'Решение верное, но категория ошибочна.',
                'mb.outcome_part_cat':   'Категория верная, но решение ошибочно. На самом деле: ',
                'mb.outcome_wrong':      'И решение, и категория неверны. На самом деле: ',
                'rl.task_badge':         'ЗАДАНИЕ',
                'rl.question_of':        'Вопрос',
                'rl.textarea_placeholder': 'Напишите анализ (минимум 20 символов)...',
                'rl.upload_solution':    '📷 Загрузить решение',
                'rl.solution_uploaded':  '✓ Решение загружено',
                'rl.upload_required':    '📷 Пожалуйста, загрузите фото вашего решения.',
                'rl.enter_answer':       'Введите ответ.',
                'rl.correct_prefix':     '✓ Верно! ',
                'rl.fill_all_fields':    'Заполните все поля.',
                'rl.all_correct':        '✓ Все поля верны!',
                'rl.field_hint':         '💡 Одно или несколько полей неверны. Проверьте ещё раз.',
                'rl.right_answers':      '✗ Правильные ответы: ',
                'rl.min_chars':          'Пожалуйста, напишите анализ минимум на 20 символов.',
                'rl.analysis_received':  '✓ Ваш анализ принят. AI проверяет...',
                'rl.ai_analyzing':       '✗ AI анализирует...',
                'rl.correct_count':      'Правильных ответов:',
                'rl.uploaded_count':     'Загруженных решений:',
                'boss.question_of':      'Вопрос',
                'boss.correct_hp':       '✓ Верно! −',
                'boss.combo_hp':         '🔥 КОМБО ×2! −',
                'boss.wrong_ai':         '✗ Неверно. AI анализирует...',
                'boss.checking':         'Проверяется…',
                'boss.wrong_next':       '✗ Неверно. Переходите к следующему вопросу.',
                'boss.combo_x2':         '🔥 Комбо ×2!',
                'boss.combo_streak':     'подряд',
                'boss.victory_correct':  'Верно:',
                'boss.victory_hints':    'Подсказок:',
                'boss.victory_hints_unit': 'шт',
                'boss.victory_damage':   'Урон по боссу:',
                'boss.victory_finish':   '§22 Завершить',
                'boss.defeat_hp':        'У босса осталось HP:',
                'boss.defeat_correct':   'Верно:',
                'boss.defeat_tip':       'Пересмотрите слабые вопросы и попробуйте снова.',
                // FB redesign (Final Boss runtime polish) — additive keys.
                'boss.attempt_of':              'Попытка {n}/{max}',
                'boss.full_damage':             'Полный удар',
                'boss.half_damage':             'Половина урона',
                'boss.no_damage':               'Без урона',
                'boss.combo_x2_activated':      '🔥 Комбо ×2 активировано!',
                'boss.low_hp_warning':          'Босс ослаб — финальный удар!',
                'boss.outcome.expert':          'Уровень эксперта',
                'boss.outcome.strong':          'Сильный анализ',
                'boss.outcome.passing':         'Зачёт',
                'boss.outcome.hali_emas':       'Пока нет',
                'boss.stars.1':                 '1 звезда — едва прошли',
                'boss.stars.2':                 '2 звезды — хорошее мастерство',
                'boss.stars.3':                 '3 звезды — Отличное мастерство!',
                'boss.hint_used_amber':         '💡 Подсказка использована · +{n} HP боссу',
                'boss.toast.wrong':             'Неверно — попробуйте ещё раз',
                'boss.toast.try_again':         'Ещё попытка',
                'boss.result.xp':               '+{n} XP',
                'boss.result.summary':          '{correct}/{total} верно · {damage} HP урона · {hints} подсказок',
                'res.headline_prefix':   'Ваш общий результат:',
                'res.correct_suffix':    'верно',
                'res.phase_done':        'Завершено',
                'res.phase_undone':      'Не выполнено',
                'res.amr_title':         'AMR — двухосевая шкала мастерства',
                'res.amr_title_short':   'AMR — 2-осевая шкала',
                'res.amr_no_ai':         'В этой сессии ни один ответ не оценивался AI (только закрытые форматы). Открытые ответы (Sentence Fill, Real-Life Q5, Boss Q3-Q5) оцениваются AI по двум осям.',
                'res.amr_axis1':         'Ось 1 — Идентификация концепта',
                'res.amr_axis2':         'Ось 2 — Корректность процесса',
                'res.amr_no_items':      'нет ответов с AI-оценкой',
                // LMR v2 — language subjects (English / Ona Tili / Rus Tili).
                'res.lmr_title':         'LMR — двухосевая шкала владения языком',
                'res.lmr_title_short':   'LMR — 2-осевая шкала',
                'res.lmr_axis1':         'Ось 1 — Грамматическая точность',
                'res.lmr_axis2':         'Ось 2 — Лексическое качество',
                'res.tip_mastered':      'Отлично! Вы полностью освоили тему. К окну продвижения мастерства добавлен 1 балл (из 3).',
                'res.tip_proficient':    'Хорошо. Вы можете работать самостоятельно. Ещё 1-2 сессии — и достигнете уровня Mastered.',
                'res.tip_apprentice':    'Есть над чем подумать. В назывании концепта или показе шагов есть пробелы — в следующих упражнениях расписывайте процесс письменно.',
                'res.tip_novice':        'Перепройдите тему. Перечитайте Hint Ladder и Flash Cards, затем попробуйте снова.',
                'res.closed_format':     'Анализ закрытых ответов: ',
                'res.closing':           'Отчёт сохранён. Следующее повторение через 1 день.',
                'gb.break_done':         'Игровой перерыв окончен!',
                // phase announcement card labels (Bug #4)
                'phase.game_breaks':     'Игровой перерыв',
                'phase.real_life':       'Жизненная задача',
                'phase.consolidation':   'Закрепление',
                'phase.reflection':      'Рефлексия',
                // sub-game announcement labels (Bug #4)
                'game.aq':               'Адаптивный тест',
                'game.wc':               'Заполнение предложения',
                'game.mm':               'Парная память',
                'game.tm':               'Tile Match',
                'game.pl':               'Замок-головоломка',
                'game.mb':               'Загадочный ящик',
                'game.ttt':              'Крестики-нолики',
                'game.sf':               'Заполнение предложения',
                // Sentence Fill (sf.*)
                'sf.title':              'Заполни пропуск',
                'sf.eyebrow':            'Игра · Cloze',
                'sf.passage_label':      'Текст',
                'sf.mode_word_bank':     'Из списка',
                'sf.mode_free_recall':   'По памяти',
                'sf.subtitle_bank':      'Выберите пропуск, затем слово.',
                'sf.subtitle_recall':    'Введите слова по памяти.',
                'sf.btn_check':          'Проверить',
                'sf.btn_next':           'Дальше',
                'sf.result_perfect':     'Идеально',
                'sf.result_partial':     'Не совсем',
                'sf.toast_perfect':      'Идеально! Бонус XP.',
                'sf.toast_partial':      'Проверено. Ответы показаны.',
                'sf.toast_locked':       'Пропуск заблокирован.',
                'sf.score_label':        'XP',
                'sf.first_attempt_bonus':'+25 (с первого раза)',
                'sf.perfect_fill_bonus': '+100 идеально',
                'sf.keyboard_hint':      'Клавиши: Tab — пропуск/слово · Enter — проверить · Backspace — очистить',
                'sf.chain_label':        'Цепочка',
                // real-life challenge (RLC) — new 5-step flow
                'rlc.eyebrow':           'REAL-LIFE CHALLENGE',
                'rlc.title':             'Решите ситуацию',
                'rlc.subtitle':          'Сделайте выбор как эксперт, напишите анализ.',
                'rlc.step.decision':     'Шаг 1 · Решение',
                'rlc.step.info':         'Шаг 2 · Запрос информации',
                'rlc.step.final':        'Шаг 3 · Финальное решение',
                'rlc.step.concept':      'Шаг 4 · Концепция',
                'rlc.step.reasoning':    'Шаг 5 · Анализ',
                'rlc.dock.continue':     'Продолжить',
                'rlc.dock.submit':       'Подтвердить',
                'rlc.dock.next':         'Следующий шаг',
                'rlc.dock.finish':       'Завершить',
                'rlc.outcome.expert_decision': 'Экспертное решение!',
                'rlc.outcome.strong_analysis': 'Сильный анализ',
                'rlc.outcome.passing':         'Зачтено',
                'rlc.outcome.hali_emas':       'Пока нет',
                'rlc.toast.correct':     'Отлично, идём дальше.',
                'rlc.toast.wrong':       'Не подходит. Подумайте ещё раз.',
                'rlc.toast.try_again':   'Попробуйте ещё раз.',
                'rlc.toast.locked':      'Шаг закрыт. Правильный ответ показан.',
                'rlc.role.fire_inspector':       'Инспектор пожарной безопасности',
                'rlc.role.structural_engineer':  'Инженер-конструктор',
                'rlc.role.business_consultant':  'Бизнес-консультант',
                'rlc.role.medical_diagnostician':'Медицинский диагност',
                'rlc.role.agronomist':           'Агроном',
                'rlc.role.teacher':              'Учитель',
                'rlc.role.lawyer':               'Юрист',
                'rlc.role.city_planner':         'Градостроитель',
                'rlc.role.epidemiologist':       'Эпидемиолог',
                'rlc.role.ethicist':             'Специалист по этике',
                'rlc.role.historian':            'Историк',
                'rlc.role.general':              'Эксперт',
                'rlc.placeholder.reasoning': 'Обоснуйте свою позицию... (минимум указанное число символов)',
                'rlc.charcount':         '{n}/{min}',
                'rlc.consequence_reveal': 'Последствие:',
                'rlc.correct_was':       'Правильный ответ:',
                // tic tac toe
                'ttt.heroEyebrow':       'Студент против AI',
                'ttt.heroTitle':         'Ваши знания управляют доской.',
                'ttt.subtitle':          'Сначала выберите целевую клетку. Правильный ответ ставит X туда. Неправильный — рассеивает в случайную пустую клетку.',
                'ttt.draws':             'Ничьи',
                'ttt.losses':            'Поражения',
                'ttt.correct':           'Правильно',
                'ttt.boardTitle':        'Тактическая доска',
                'ttt.boardCopy':         'Выберите клетку, чтобы бросить вызов AI.',
                'ttt.boardCopyAnswer':   'Правильный ответ — X идёт в выбранную клетку. Неправильный — в случайную.',
                'ttt.boardCopyAI':       'AI играет оптимально. Лучший реалистичный исход — ничья.',
                'ttt.turnYour':          'Ваш ход',
                'ttt.turnAI':            'AI думает',
                'ttt.turnAnswer':        'Сначала ответьте',
                'ttt.stageLabel':        'Ответьте, чтобы занять клетку',
                'ttt.feedbackCorrect':   'Правильно. X встал ровно в нужную клетку. +50 XP.',
                'ttt.feedbackWrong':     'Неправильно. X улетел в случайную пустую клетку.',
                'ttt.feedbackMercy':     'Неправильно, но повезло. X всё-таки встал в нужную клетку.',
                'ttt.resultWinTitle':    'Невозможное случилось',
                'ttt.resultWinText':     'Вы обыграли оптимальный AI. В стандартном режиме это почти невозможно.',
                'ttt.resultDrawTitle':   'Удержали линию',
                'ttt.resultDrawText':    'Ничья достигнута. Против оптимального AI это и есть лучший реалистичный исход.',
                'ttt.resultLossTitle':   'Hali emas',
                'ttt.resultLossText':    'AI выиграл. Это диагностика, не повод стыдиться. Неправильные ответы обычно и стоят контроля над доской.',
                'ttt.sessionStrongTitle': 'Сильная сессия',
                'ttt.sessionStrongText': '2+ ничьи. Тактический бонус начислен.',
                'ttt.sessionSolidTitle': 'Хорошая сессия',
                'ttt.sessionSolidText':  'Одна ничья и стабильный XP за правильные ответы. Продолжайте оттачивать контроль доски.',
                'ttt.sessionFailedTitle': 'Задача не решена',
                'ttt.sessionFailedText': '0 ничьих. Нужно повторить материал.',
                'ttt.sessionXP':         'Сессия XP',
                'ttt.dockTap':           'Нажмите клетку',
                'ttt.dockAnswer':        'Ответьте на вопрос',
                'ttt.dockNext':          'Следующая игра',
                'ttt.dockResult':        'Итог сессии',
                'ttt.dockComplete':      'Сессия завершена',
                'ttt.duolingoToast':     'Нужно повторить упражнения — начнём с коротких.',
                // Memory Palace (mp.*) — 4-step Method of Loci flow, panel: gb-panel-mp
                'game.mp':               'Дворец памяти',
                'mp.heroKicker':         'Метод локусов',
                'mp.heroTitleStep1':     'Постройте мысленный маршрут.',
                'mp.heroTitleStep2':     'Привяжите понятие к месту.',
                'mp.heroTitleStep3':     'Пройдитесь по дворцу.',
                'mp.heroTitleStep4':     'Извлеките из памяти.',
                'mp.heroSubStep1':       'Выберите дворец, релевантный теме — каждое место должно сочетаться с уроком.',
                'mp.heroSubStep2':       'Поместите каждое понятие в место с ярким, преувеличенным образом.',
                'mp.heroSubStep3':       'Пройдите маршрут по порядку. Усильте каждую связь место—понятие.',
                'mp.heroSubStep4':       'Отвечайте по подсказке локации. Сильная пространственная привязка — лёгкое извлечение.',
                'mp.step1Label':         '1-й шаг · Выбрать дворец',
                'mp.step2Label':         '2-й шаг · Разместить понятия',
                'mp.step3Label':         '3-й шаг · Мысленная прогулка',
                'mp.step4Label':         '4-й шаг · Тест на воспоминание',
                'mp.placementOccupied':  'Хранится: {term}',
                'mp.conceptCounter':     'Понятие {n}/{total}',
                'mp.walkCounter':        'Остановка {n}/{total}',
                'mp.recallCounter':      'Вопрос {n}/{total}',
                'mp.recallQuestion':     'Какое понятие вы привязали к этому месту?',
                'mp.feedbackCorrect':    'Верно. Связь место—понятие крепкая.',
                'mp.feedbackWrong':      'Пока нет. Эту связь нужно ещё раз пройти.',
                'mp.outcome.perfect':    'Отлично!',
                'mp.outcome.yaxshi':     'Хорошо!',
                'mp.outcome.hali_emas_partial': 'Пока нет',
                'mp.outcome.hali_emas_fail':    'Пока нет',
                'mp.level.apprentice':   'Ученик',
                'mp.level.proficient':   'Уверенно',
                'mp.level.mastered':     'Мастер',
                'mp.level.pending':      'Начинающий',
                'mp.accuracyLabel':      'Точность',
                'mp.speedLabel':         'Скорость воспоминания',
                'mp.levelLabel':         'Уровень',
                'mp.xpLabel':            'XP сессии',
                'mp.dockChoosePalace':   'Выберите дворец',
                'mp.dockPlaceConcept':   'Разместите понятие',
                'mp.dockStartWalk':      'Начать прогулку',
                'mp.dockNextStop':       'Следующее место',
                'mp.dockAnswerRecall':   'Ответить на вопрос',
                'mp.dockComplete':       'Дворец готов',
                'mp.dockRetry':          'Попробовать снова',
                'mp.toastNetwork':       'Проблема с сетью. Показан локальный результат.',
            },
            en: {
                'skip.label':            '⏭ Skip phase',
                'btn.continue':          'Continue',
                'btn.next':              'Next',
                'btn.next_page':         'Next page',
                'btn.next_panel':        'Next panel',
                'btn.finish':            'Finish',
                'btn.start':             'Start',
                'btn.confirm':           'Confirm',
                'btn.check_answer':      'Check answer',
                'btn.submit_answer':     'Submit',
                'btn.next_question':     'Next question',
                'btn.next_stage':        'Next stage',
                'btn.next_game':         'Next game',
                'btn.next_chain':        'Next chain',
                'btn.next_box':          'Next box',
                'btn.complete':          'Complete',
                'btn.retry':             'Try again',
                'btn.game_break':        'Game break',
                'btn.read':              'Go to reading',
                'btn.submit_response':   'Submit answer',
                'btn.send':              'Send answer',
                'btn.show_hint':         '💡 Show hint',
                'btn.hide_hint':         '💡 Hide hint',
                'btn.ask_tutor':         '💬 Tutor',
                'rl.ai_unavailable_wrong': 'Answer received. AI is temporarily unavailable.',
                'verdict.correct':       '✓ Correct!',
                'verdict.wrong':         '✗ Wrong.',
                'verdict.right_answer':  'Correct answer:',
                'reading.title_default': 'Reading',
                'reading.placeholder':   'Type your answer...',
                'reading.check':         'Check',
                'reading.next_question': 'Next question',
                'reading.page_label':    'Page',
                'reading.must_answer':   'Answer the checkpoint to continue.',
                'reading.all_done':      'Reading checkpoint complete. You can continue.',
                'reading.correct':       '✓ Correct!',
                'reading.wrong':         '✗ Wrong.',
                'reading.right_answer':  'Correct answer:',
                'reading.ai_correct_default': 'Correct!',
                'cons.title_default':    'Consolidation',
                'cons.expected_prefix':  'Expected answer: ',
                'cons.show_answer':      'Show answer',
                'ms.question_prefix':    'Q',
                'ms.score_great':        'Great. You caught the sprint rhythm and recalled the key terms fast.',
                'ms.score_meh':          'Not yet. But the sprint worked — now you know what needs another pass.',
                'aq.question_of':        'Q',
                'aq.upload_solution':    'Upload your solution (📷)',
                'aq.solution_uploaded':  '📷 Your solution is uploaded',
                'aq.upload_first':       'Upload your solution first!',
                'aq.correct_prefix':     'Correct! ',
                'aq.wrong_prefix':       'Wrong. Correct answer: ',
                // adaptive quiz — Apple-glass redesign labels (2026-05-01)
                'aq.tier_easy':          'Easy',
                'aq.tier_medium':        'Medium',
                'aq.tier_hard':          'Hard',
                'aq.answer_label':       'Answer',
                'aq.answer_help':        'Write your final answer.',
                'aq.status_step1':       'Step 1',
                'aq.status_upload_done': 'Uploaded',
                'aq.status_correct':     'Correct',
                'aq.status_review':      'Review',
                'aq.upload_drop_label':  'Confirm your solution',
                'aq.upload_subtitle':    'Your answer is saved. Attach the worked solution.',
                'wc.chain_label':        'Chain',
                'wc.level_label':        'Level',
                'wc.checking':           'Checking…',
                'wc.right_answer':       'Correct answer: ',
                'tm.pairs_status':       'Find pairs:',
                'tm.eyebrow':            'GAME 3 · MATCH',
                'tm.title':              'Match concept to meaning.',
                'tm.subtitle':           'Pick one tile from the left, then one from the right. Correct pairs fade away, wrong pairs gently shake.',
                'tm.col_left':           'Concept',
                'tm.col_right':          'Definition',
                'tm.stats_matched':      'Matched',
                'tm.stats_wrong':        'Wrong',
                'tm.toast_correct':      'Correct! +100 XP.',
                'tm.toast_streak':       '3-match streak! +50 XP',
                'tm.toast_wrong':        'Not a match.',
                'tm.toast_pick_left':    'Pick a left tile first.',
                'tm.toast_perfect_clear': 'Perfect! Zero wrong.',
                'tm.result_perfect':     'Perfect Clear',
                'tm.result_flawless':    'Flawless',
                'tm.result_cleared':     'Cleared',
                'tm.result_not_yet':     'Not yet',
                'tm.result_body_perfect': 'Zero wrong attempts. Remember this — that focus is your edge.',
                'tm.result_body_flawless': 'Just one wrong attempt. Strong run.',
                'tm.result_body_cleared': 'All pairs matched.',
                'tm.result_body_partial': 'Time ran out. Try the board again.',
                'tm.dock_select':        'Select a pair',
                'tm.dock_choose_meaning': 'Choose meaning',
                'tm.dock_next_game':     'Next game',
                'tm.dock_replay':        'Replay board',
                'tm.hint_correct':       'Correct: ',
                'tm.xp_label':           'Tile Match XP',
                'pl.fit_status':         'In place:',
                'pl.no_question':        '(no question)',
                'pl.step_status':        'Step {n} / {total}',
                'pl.step_locked':        'Solve the previous step first',
                'pl.wrong_feedback':     'Not quite — try again.',
                'mb.boxes_status':       'Boxes:',
                'mb.right_category':     'Right category!',
                'mb.actually_prefix':    "It's actually — ",
                'mb.outcome_correct':    'Correct — category and answer match!',
                'mb.outcome_part_ans':   'Answer is right, but category is wrong.',
                'mb.outcome_part_cat':   "Category is right, but answer is wrong. It's actually: ",
                'mb.outcome_wrong':      "Both answer and category wrong. It's actually: ",
                'rl.task_badge':         'TASK',
                'rl.question_of':        'Q',
                'rl.textarea_placeholder': 'Write your analysis (at least 20 characters)...',
                'rl.upload_solution':    '📷 Upload solution',
                'rl.solution_uploaded':  '✓ Solution uploaded',
                'rl.upload_required':    '📷 Please also upload a photo of your solution.',
                'rl.enter_answer':       'Enter an answer.',
                'rl.correct_prefix':     '✓ Correct! ',
                'rl.fill_all_fields':    'Fill in all fields.',
                'rl.all_correct':        '✓ All fields correct!',
                'rl.field_hint':         '💡 One or more fields are wrong. Check again.',
                'rl.right_answers':      '✗ Correct answers: ',
                'rl.min_chars':          'Please write at least 20 characters.',
                'rl.analysis_received':  '✓ Analysis received. AI is grading...',
                'rl.ai_analyzing':       '✗ AI analyzing...',
                'rl.correct_count':      'Correct answers:',
                'rl.uploaded_count':     'Uploads:',
                'boss.question_of':      'Q',
                'boss.correct_hp':       '✓ Correct! −',
                'boss.combo_hp':         '🔥 COMBO ×2! −',
                'boss.wrong_ai':         '✗ Wrong. AI analyzing...',
                'boss.checking':         'Checking…',
                'boss.wrong_next':       '✗ Wrong. Move to the next question.',
                'boss.combo_x2':         '🔥 Combo ×2!',
                'boss.combo_streak':     'in a row',
                'boss.victory_correct':  'Correct:',
                'boss.victory_hints':    'Hints used:',
                'boss.victory_hints_unit': '',
                'boss.victory_damage':   'Boss damage dealt:',
                'boss.victory_finish':   '§22 Finish',
                'boss.defeat_hp':        'Boss HP remaining:',
                'boss.defeat_correct':   'Correct:',
                'boss.defeat_tip':       'Review the weak questions and try again.',
                // FB redesign (Final Boss runtime polish) — additive keys.
                'boss.attempt_of':              'Attempt {n}/{max}',
                'boss.full_damage':             'Full damage',
                'boss.half_damage':             'Half damage',
                'boss.no_damage':               'No damage',
                'boss.combo_x2_activated':      '🔥 Combo ×2 activated!',
                'boss.low_hp_warning':          'Boss weakened — finishing blow!',
                'boss.outcome.expert':          'Expert level',
                'boss.outcome.strong':          'Strong mastery',
                'boss.outcome.passing':         'Passing',
                'boss.outcome.hali_emas':       'Not yet',
                'boss.stars.1':                 '1 star — barely through, but through',
                'boss.stars.2':                 '2 stars — solid mastery',
                'boss.stars.3':                 '3 stars — Outstanding mastery!',
                'boss.hint_used_amber':         '💡 Hint used · +{n} HP to boss',
                'boss.toast.wrong':             'Wrong — try again',
                'boss.toast.try_again':         'Try again',
                'boss.result.xp':               '+{n} XP',
                'boss.result.summary':          '{correct}/{total} correct · {damage} HP damage · {hints} hints',
                'res.headline_prefix':   'Your overall score:',
                'res.correct_suffix':    'correct',
                'res.phase_done':        'Done',
                'res.phase_undone':      'Not done',
                'res.amr_title':         'AMR — 2-axis Anchored Mastery Rubric',
                'res.amr_title_short':   'AMR — 2-axis rubric',
                'res.amr_no_ai':         'No answer was AI-graded this session (closed-format only). Open-ended responses (Sentence Fill, Real-Life Q5, Boss Q3-Q5) get 2-axis AI grading.',
                'res.amr_axis1':         'Axis 1 — Concept Identification',
                'res.amr_axis2':         'Axis 2 — Process Integrity',
                'res.amr_no_items':      'no AI-graded items',
                // LMR v2 — language subjects (English / Ona Tili / Rus Tili).
                'res.lmr_title':         'LMR — 2-axis Language Mastery Rubric',
                'res.lmr_title_short':   'LMR — 2-axis rubric',
                'res.lmr_axis1':         'Axis 1 — Grammatical Accuracy',
                'res.lmr_axis2':         'Axis 2 — Lexical Quality',
                'res.tip_mastered':      'Excellent! You have mastered this topic. +1 point added to the mastery promotion window (out of 3).',
                'res.tip_proficient':    'Good. You can work independently. Another 1-2 sessions and you reach Mastered.',
                'res.tip_apprentice':    'Worth a re-look. There are gaps in naming the concept or showing the steps — write the process out next time.',
                'res.tip_novice':        'Revisit the topic. Re-read the Hint Ladder and Flash Cards, then try again.',
                'res.closed_format':     'Closed-format analysis: ',
                'res.closing':           'Report saved. Next review in 1 day.',
                'gb.break_done':         'Game break finished!',
                // phase announcement card labels (Bug #4)
                'phase.game_breaks':     'Game Break',
                'phase.real_life':       'Real-Life Challenge',
                'phase.consolidation':   'Consolidation',
                'phase.reflection':      'Reflection',
                // sub-game announcement labels (Bug #4)
                'game.aq':               'Adaptive Quiz',
                'game.wc':               'Sentence Fill',
                'game.mm':               'Tile Match',
                'game.tm':               'Tile Match',
                'game.pl':               'Puzzle Lock',
                'game.mb':               'Mystery Box',
                'game.ttt':              'Tic Tac Toe',
                'game.sf':               'Sentence Fill',
                // Sentence Fill (sf.*)
                'sf.title':              'Sentence Fill',
                'sf.eyebrow':            'Game · Cloze',
                'sf.passage_label':      'Passage',
                'sf.mode_word_bank':     'Word bank',
                'sf.mode_free_recall':   'Free recall',
                'sf.subtitle_bank':      'Tap a blank, then pick a word.',
                'sf.subtitle_recall':    'Type each word from memory.',
                'sf.btn_check':          'Check',
                'sf.btn_next':           'Next',
                'sf.result_perfect':     'Perfect Fill',
                'sf.result_partial':     'Not quite',
                'sf.toast_perfect':      'Perfect. Bonus XP.',
                'sf.toast_partial':      'Checked. Corrections revealed.',
                'sf.toast_locked':       'Blank locked.',
                'sf.score_label':        'Sentence Fill XP',
                'sf.first_attempt_bonus':'+25 (first try)',
                'sf.perfect_fill_bonus': '+100 perfect fill',
                'sf.keyboard_hint':      'Keys: Tab — blanks/words · Enter — check · Backspace — clear',
                'sf.chain_label':        'Chain',
                // real-life challenge (RLC) — new 5-step flow
                'rlc.eyebrow':           'REAL-LIFE CHALLENGE',
                'rlc.title':             'Resolve the situation',
                'rlc.subtitle':          'Make an expert call, then explain your reasoning.',
                'rlc.step.decision':     'Step 1 · Decision',
                'rlc.step.info':         'Step 2 · Info request',
                'rlc.step.final':        'Step 3 · Final decision',
                'rlc.step.concept':      'Step 4 · Concept',
                'rlc.step.reasoning':    'Step 5 · Reasoning',
                'rlc.dock.continue':     'Continue',
                'rlc.dock.submit':       'Submit',
                'rlc.dock.next':         'Next step',
                'rlc.dock.finish':       'Finish',
                'rlc.outcome.expert_decision': 'Expert decision!',
                'rlc.outcome.strong_analysis': 'Strong analysis',
                'rlc.outcome.passing':         'Passing',
                'rlc.outcome.hali_emas':       'Not yet',
                'rlc.toast.correct':     'Nice, moving on.',
                'rlc.toast.wrong':       "That doesn't fit. Reconsider.",
                'rlc.toast.try_again':   'Try again.',
                'rlc.toast.locked':      'Step locked. Correct answer revealed.',
                'rlc.role.fire_inspector':       'Fire-safety inspector',
                'rlc.role.structural_engineer':  'Structural engineer',
                'rlc.role.business_consultant':  'Business consultant',
                'rlc.role.medical_diagnostician':'Medical diagnostician',
                'rlc.role.agronomist':           'Agronomist',
                'rlc.role.teacher':              'Teacher',
                'rlc.role.lawyer':               'Lawyer',
                'rlc.role.city_planner':         'City planner',
                'rlc.role.epidemiologist':       'Epidemiologist',
                'rlc.role.ethicist':             'Ethicist',
                'rlc.role.historian':            'Historian',
                'rlc.role.general':              'Expert',
                'rlc.placeholder.reasoning': 'Justify your call (meet the minimum char count)...',
                'rlc.charcount':         '{n}/{min}',
                'rlc.consequence_reveal': 'Consequence:',
                'rlc.correct_was':       'Correct answer:',
                // tic tac toe
                'ttt.heroEyebrow':       'Student vs AI',
                'ttt.heroTitle':         'Your knowledge controls the board.',
                'ttt.subtitle':          'Tap your target cell first. Correct answer lands your X there. Wrong answer scatters it to a random empty cell.',
                'ttt.draws':             'Draws',
                'ttt.losses':            'Losses',
                'ttt.correct':           'Correct',
                'ttt.boardTitle':        'Tactical Board',
                'ttt.boardCopy':         'Tap a cell to challenge the AI.',
                'ttt.boardCopyAnswer':   'Correct answer claims your intended cell. Wrong answer scatters your move.',
                'ttt.boardCopyAI':       'The AI plays optimally. Your best realistic outcome is a draw.',
                'ttt.turnYour':          'Your move',
                'ttt.turnAI':            'AI thinking',
                'ttt.turnAnswer':        'Answer first',
                'ttt.stageLabel':        'Answer to claim cell',
                'ttt.feedbackCorrect':   'Correct. Your X lands exactly where you intended. +50 XP.',
                'ttt.feedbackWrong':     'Wrong. Your X scattered to a random empty cell.',
                'ttt.feedbackMercy':     'Wrong, but lucky bounce. Your X still landed on the intended cell.',
                'ttt.resultWinTitle':    'Impossible Happened',
                'ttt.resultWinText':     'You beat optimal AI. This should be almost impossible in standard mode.',
                'ttt.resultDrawTitle':   'Held the Line',
                'ttt.resultDrawText':    'Draw achieved. Against optimal AI, this is the realistic best outcome.',
                'ttt.resultLossTitle':   'Hali emas',
                'ttt.resultLossText':    'AI won. This is diagnostic, not shame. Wrong-answer scatter moves are what usually cost control.',
                'ttt.sessionStrongTitle': 'Strong Session',
                'ttt.sessionStrongText': '2+ draws achieved. Tactician bonus added.',
                'ttt.sessionSolidTitle': 'Solid Session',
                'ttt.sessionSolidText':  'One draw and continued XP from correct answers. Keep sharpening board control.',
                'ttt.sessionFailedTitle': 'Task Failed',
                'ttt.sessionFailedText': '0 draws. Time to re-serve micro-drills before advancing.',
                'ttt.sessionXP':         'Session XP',
                'ttt.dockTap':           'Tap a cell',
                'ttt.dockAnswer':        'Answer question',
                'ttt.dockNext':          'Next game',
                'ttt.dockResult':        'Session result',
                'ttt.dockComplete':      'Session complete',
                'ttt.duolingoToast':     'Time to revisit fundamentals — micro-drills coming up.',
                // Memory Palace (mp.*) — 4-step Method of Loci flow, panel: gb-panel-mp
                'game.mp':               'Memory Palace',
                'mp.heroKicker':         'Method of Loci',
                'mp.heroTitleStep1':     'Build a mental route.',
                'mp.heroTitleStep2':     'Anchor a concept to a place.',
                'mp.heroTitleStep3':     'Walk through your palace.',
                'mp.heroTitleStep4':     'Retrieve from memory.',
                'mp.heroSubStep1':       'Pick a palace relevant to the topic — each location should fit the lesson naturally.',
                'mp.heroSubStep2':       'Place each concept in a vivid, exaggerated image you cannot forget.',
                'mp.heroSubStep3':       'Walk the route in order. Reinforce each location-concept bond.',
                'mp.heroSubStep4':       'Answer from the location cue. Strong spatial anchors make recall feel easy.',
                'mp.step1Label':         'Step 1 · Choose palace',
                'mp.step2Label':         'Step 2 · Place concepts',
                'mp.step3Label':         'Step 3 · Walkthrough',
                'mp.step4Label':         'Step 4 · Recall test',
                'mp.placementOccupied':  'Holding: {term}',
                'mp.conceptCounter':     'Concept {n}/{total}',
                'mp.walkCounter':        'Stop {n}/{total}',
                'mp.recallCounter':      'Question {n}/{total}',
                'mp.recallQuestion':     'What concept did you place here?',
                'mp.feedbackCorrect':    'Correct. Location bond is strong.',
                'mp.feedbackWrong':      'Not yet. This bond needs another walkthrough.',
                'mp.outcome.perfect':    'Excellent!',
                'mp.outcome.yaxshi':     'Good work!',
                'mp.outcome.hali_emas_partial': 'Not yet',
                'mp.outcome.hali_emas_fail':    'Not yet',
                'mp.level.apprentice':   'Apprentice',
                'mp.level.proficient':   'Proficient',
                'mp.level.mastered':     'Mastered',
                'mp.level.pending':      'Pending',
                'mp.accuracyLabel':      'Accuracy',
                'mp.speedLabel':         'Recall Speed',
                'mp.levelLabel':         'Level',
                'mp.xpLabel':            'Session XP',
                'mp.dockChoosePalace':   'Choose palace',
                'mp.dockPlaceConcept':   'Place concept',
                'mp.dockStartWalk':      'Start walk',
                'mp.dockNextStop':       'Next location',
                'mp.dockAnswerRecall':   'Answer recall',
                'mp.dockComplete':       'Palace complete',
                'mp.dockRetry':          'Retry palace',
                'mp.toastNetwork':       'Network issue. Showing local result.',
            },
        };

        function _runtimeDetectLang() {
            const ctx = window.NETS_CTX || {};
            const raw = (ctx.lang || document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
            return RUNTIME_LABELS[raw] ? raw : 'en';
        }

        function RT(key) {
            const lang = _runtimeDetectLang();
            const tbl = RUNTIME_LABELS[lang] || RUNTIME_LABELS.en;
            return tbl[key] || RUNTIME_LABELS.en[key] || RUNTIME_LABELS.uz[key] || key;
        }
        // Expose globally so the tutor IIFE (and any future scope) can read it.
        window.RT = RT;
        window.RUNTIME_LABELS = RUNTIME_LABELS;

        // Localize the static skip-pill markup once the DOM is ready.
        document.addEventListener('DOMContentLoaded', function () {
            const sp = document.getElementById('skip-pill');
            if (sp) sp.textContent = RT('skip.label');
        });

        // Resolve boss name from injected runtime context (NETS_CTX.boss_name)
        // and write it into the data-boss-name / data-boss-name-label hooks T1
        // pre-laid in the boss-intro markup. Server-side defaults already
        // pick a subject-appropriate name; missing/empty value is a no-op so
        // the static template fallback ("Algebra Boshlig'i") stays visible.
        document.addEventListener('DOMContentLoaded', function populateBossName(){
            try {
                var name = (window.NETS_CTX && window.NETS_CTX.boss_name) || '';
                if (!name) return;
                document.querySelectorAll('[data-boss-name]').forEach(function(el){
                    el.textContent = name;
                });
                document.querySelectorAll('[data-boss-name-label]').forEach(function(el){
                    // Preserve any leading non-word prefix (e.g. "⚔️ ") and only
                    // swap the name portion. \W matches the emoji + spaces.
                    var prev = el.textContent || '';
                    var m = prev.match(/^(\W*)/);
                    var prefix = m ? m[1] : '';
                    el.textContent = prefix + name;
                });
            } catch (e) { /* defensive — non-fatal if hooks missing */ }
        });

        const PANELS = [
            {
                id: 1,
                title: "PANEL 1 — XULOSA",
                pages: [
                    {
                        blocks: [
                            {type: "p", text: "Kvadrat tenglama — noma'lumning kvadratda uchragan har qanday tenglama. Standart shakli:"},
                            {type: "quote", text: "ax² + bx + c = 0"},
                            {type: "p", text: "bunda a, b, c — masala beradigan sonlar, va a ≠ 0 muhim — agar a nol bo'lsa, x² hadi yo'qoladi va sizda faqat chiziqli tenglama bx + c = 0 qoladi, uni yechishni allaqachon bilasiz."},
                            {type: "p", text: "Ushbu bo'lim uchta ko'nikmani shakllantiradi:"},
                            {type: "ol", items: [
                                "Kvadrat tenglamani ko'rganingizda uni aniqlash",
                                "Eng sodda holat x² = d ni yechish",
                                "Sonlar chiroyli kelishganda ko'paytuvchilarga ajratish orqali yechish"
                            ]},
                            {type: "p", text: "Yana ikkita yechish usuli — to'liq kvadratga keltirish va to'liq kvadrat tenglama formulasi — 24 va 25-bo'lmlarda joylashgan. Bugun poydevor."},
                            {type: "p", text: "<strong>Sodda so'zlar bilan:</strong><br>Kvadrat — ichida x² bo'lgan har qanday tenglama. Sizning vazifangiz x ni topish. Buni qilishning bir necha yo'li bor va ushbu bo'lim sizga eng oson ikkitasini ko'rsatadi. Qiyinroq usullar keyingilarda keladi."}
                        ]
                    }
                ]
            },
            {
                id: 2,
                title: "PANEL 2 — YAXSHIROQ TUSHUNTIRISH",
                pages: [
                    {
                        blocks: [
                            {type: "h2", text: "① Ko'paytuvchilarga ajratish bo'linishi orqasida qoida bor"},
                            {type: "p", text: "x² + 10x – 24 = 0 tenglamasini guruhlash usuli bilan yechayotganda, biz quyidagicha yozamiz:"},
                            {type: "quote", text: "x² + 10x – 24 = x² + 12x – 2x – 24 = x(x + 12) – 2(x + 12) = (x + 12)(x – 2)"},
                            {type: "p", text: "10x = 12x – 2x bo'linishi hech qayerdan paydo bo'lgandek ko'rinadi. Aslida unday emas — orqasida qoida bor. Keling, uni ochib beraylik."},
                            {type: "p", text: "Biz (x + p)(x + q) ko'rinishida ko'paytuvchilarga ajratmoqchimiz. Agar uni ochsak:"},
                            {type: "quote", text: "(x + p)(x + q) = x² + (p + q)·x + p·q"},
                            {type: "p", text: "Endi bizning tenglamamiz x² + 10x – 24 bilan solishtiramiz. Hadma-had solishtirish:"},
                            {type: "ul", items: [
                                "p + q = 10 (o'rta koeffitsient)",
                                "p · q = –24 (ozod had)"
                            ]},
                            {type: "p", text: "Shunday qilib, bizga 10 ga yig'indisi va –24 ga ko'paytmasi teng bo'lgan ikkita son kerak. –24 ning har mumkin bo'lgan ko'paytuvchi juftlarini ro'yxatlang va har bir yig'indini tekshiring:"},
                            {type: "code", text: "┌─────────────┬──────────┐\n│    p, q     │  p + q   │\n├─────────────┼──────────┤\n│   1, –24    │   –23    │\n│  –1,  24    │    23    │\n│   2, –12    │   –10    │\n│  –2,  12    │    10  ← ✓ g'olib\n│   3,  –8    │    –5    │\n│  –3,   8    │     5    │\n│   4,  –6    │    –2    │\n│  –4,   6    │     2    │\n└─────────────┴──────────┘"},
                            {type: "p", text: "Faqat bitta juft ishlaydi: (–2, 12). Shuning uchun kitob 10x ni 12x – 2x ga bo'ladi va, masalan, 7x + 3x emas — (7, 3) jufti –24 ga ko'paymaydi. Bo'linish bu qidiruv natijasi, omadli taxmin emas."},
                            {type: "p", text: "<strong>Sodda so'zlar bilan:</strong><br>Ko'paytuvchilarga ajratish uchun ikkita son toping. Ularning yig'indisi o'rta koeffitsientga teng bo'lishi kerak. Ularning ko'paytmasi oxirgi songa teng bo'lishi kerak. Ko'paytuvchi juftlarining qisqa jadvalini tuzing va yig'indilarni tekshiring. Faqat bitta juft ishlaydi — shu sizning ko'paytuvchingiz."}
                        ]
                    },
                    {
                        blocks: [
                            {type: "h2", text: "② Ikki javob, bitta haqiqat"},
                            {type: "p", text: "Kvadrat tenglamalar odatda ikkita yechim beradi. Ba'zan ikkala javob ham haqiqiy dunyoda ishlaydi. Ba'zan faqat bittasi. Ba'zan hech biri."},
                            {type: "p", text: "Tenglama o'zi to'rtburchak, otilgan to'p yoki chipta narxi haqida ekanini bilmaydi. U faqat x ning har bir matematik jihatdan to'g'ri qiymatini qaytaradi. Siz muammo haqiqatan nimani anglatishiga qarab filtrlaysiz."},
                            {type: "p", text: "1-masalada tenglama bizga x = 2 va x = –12 berdi. Ikkalasi ham matematik jihatdan to'g'ri yechimlar. Lekin muammo balandlikni so'radi va balandliklar manfiy bo'lishi mumkin emas, shuning uchun biz x = 2 ni saqlab, x = –12 ni tashlab yuboramiz. Bu normal va kutilgan. Uzunlik, vaqt yoki son muammosiga manfiy javob ko'rsangiz, bu tenglama o'z ishini qilmoqda — siz uni tashlab yuborasiz."},
                            {type: "p", text: "<strong>Sodda so'zlar bilan:</strong><br>Kvadratlar sizga ikkita javob beradi. Matematika har doim ikkisini ham topshiradi. Keyin tekshirasiz: har bir javob ushbu muammoga mos keladimi? Mos keladiganlarni saqlang, mos kelmaydiganlarni tashlab yuboring."}
                        ]
                    },
                    {
                        blocks: [
                            {type: "h2", text: "③ Kvadrat ildizlar vs ko'paytuvchilarga ajratish — qaysi birini qachon ishlatish"},
                            {type: "p", text: "Toza holat x² = d uchun (chap tomonda faqat x², o'ng tomonda son) eng tez harakat — ikkala tomondan ham kvadrat ildiz olish:"},
                            {type: "quote", text: "x² = d → x = ±√d"},
                            {type: "p", text: "Bir qadam, bir qator, tayyor."},
                            {type: "p", text: "To'liq shakl ax² + bx + c = 0 (uch had) uchun faqat kvadrat ildiz olish ishlamaydi — yonida bx o'tirganida x² ni ajratib olishning iloji yo'q. Sizga ko'paytuvchilarga ajratish, to'liq kvadratga keltirish yoki kvadrat tenglama formulasi kerak."},
                            {type: "p", text: "Shunday qilib, nima uchun darslik x² = 64 ni uzun yo'l bilan, ko'paytuvchilarga ajratish orqali yechadi, faqat ildiz olish o'rniga? Bu isinish mashqi. x² = 64 da mashq qilayotgan xuddi shu ko'paytuvchilarga ajratish texnikasi keyinchalik x² + 5x + 6 = 0 muammosida kerak bo'ladi. Ikkala usul ham x² = 64 uchun ±8 beradi — bir xil javob — lekin faqat ko'paytuvchilarga ajratish qiyinroq muammolarda omon qoladi."},
                            {type: "code", text: "  sodda holat                     to'liq holat\n  ───────────                     ─────────\n  x² = d                          ax² + bx + c = 0\n  |                               |\n  ildizdan foydalaning → x = ±√d  ildiz ishlamaydi\n                                  |\n                                  ko'paytuvchilarga ajrating, yoki\n                                  to'liq kvadratga keltiring, yoki\n                                  formuladan foydalaning"},
                            {type: "p", text: "<strong>Sodda so'zlar bilan:</strong><br>Ikkita usul. Kvadrat ildiz tez, lekin faqat tenglama x² = son bo'lganda ishlaydi. Ko'paytuvchilarga ajratish sekinroq, lekin ko'proq tenglamalar bilan ishlaydi. Darslik sizga avval oson muammoda ko'paytuvchilarga ajratishni ko'rsatadi, shunda kerak bo'lganda qulay bo'lasiz."}
                        ]
                    },
                    {
                        blocks: [
                            {type: "h2", text: "④ ±√d belgisi va (√d)² qayta yozish"},
                            {type: "p", text: "Nima uchun ± belgisi? √64 ni olsangiz, konventsiya bo'yicha faqat musbat javob olasiz — √64 = 8, –8 emas. Bu arifmetik kvadrat ildiz deb ataladi. Lekin x² = 64 tenglamasining ikkita yechimi bor, chunki ham 8, ham –8 ning kvadrati 64. Ikkisini ham bitta belgida ifodalash uchun biz quyidagicha yozamiz:"},
                            {type: "quote", text: "x₁,₂ = ±√64 = ±8"},
                            {type: "p", text: "± \"javobni qo'shish VA ayirish\" degani. Bu ikkita sonni bir nafasda yozishning qisqacha usuli."},
                            {type: "p", text: "Nima uchun d ni (√d)² qilib qayta yozamiz? Chunki kvadrat ildiz qanday aniqlanishiga qarab. d ning kvadrat ildizi so'zma-so'z \"kvadrati d ga teng bo'lgan son\". Shunday qilib, agar kvadrat ildizni kvadratlatsangiz, asl songa qaytasiz:"},
                            {type: "quote", text: "(√d)² = d   — har doim, har qanday d ≥ 0 uchun"},
                            {type: "p", text: "Darslik bu qayta yozishdan x² – d = 0 ni x² – (√d)² = 0 ga aylantirish uchun foydalanadi. Nega bezovta? Chunki endi u allaqachon bilgan narsangizga mos keladi — kvadratlar ayirmasi a² – b² = (a – b)(a + b):"},
                            {type: "quote", text: "x² – (√d)² = (x – √d)(x + √d) = 0"},
                            {type: "p", text: "Undan keyin, x = √d yoki x = –√d. Xuddi shu ±√d javobi, taxmindan emas, naqshdan toza kelib chiqadi."},
                            {type: "p", text: "<strong>Sodda so'zlar bilan:</strong><br>√64 o'zidan musbat 8 ni anglatadi. Lekin x² = 64 tenglamasining ikkita javobi bor, +8 va –8. ± ikkisini ham bitta belgiga joylashtiradi. Va d ni (√d)² ga almashtirish mumkin, chunki bu so'zma-so'z kvadrat ildizning ma'nosi — kvadrat ildizni kvadratlash sizni songa qaytaradi. Bu foydaliroq shaklda qayta yozish, yangi hiyl emas."}
                        ]
                    }
                ]
            },
            {
                id: 3,
                title: "PANEL 3 — KELIB CHIQISHI",
                pages: [
                    {
                        blocks: [
                            {type: "p", text: "Kvadrat tenglamalar 4000 yillik. Siz ular bilan o'tirgan birinchi odam emassiz."},
                            {type: "p", text: "Mil. av. ~2000, Bobil. Mirzaboplar loy tabletkalarga quyidagicha muammolar bilan klin simvol bosdi:"},
                            {type: "quote", text: "\"Dalaning maydoni 24. Uzunligi kengligidan 10 ga ko'p. Ikkala o'lchamni toping.\""},
                            {type: "p", text: "Bu sizning darsligingizdagi 1-muammo, to'rt ming yil avval boshqa tilda boshqa vosita ustida yozilgan. Xuddi shu insoniy ehtiyoj — soliq ro'yxatlari, meros, qurilish uchun yer o'lchash — asl savolni keltirdi."},
                            {type: "p", text: "Bobilliklarning algebraik belgilanishi, manfiy sonlar, nol yo'q edi. Shuning uchun ular kvadratlarni geometrik yechdi: to'rtburchakni chizib, uni bo'laklarga kesib va bo'laklarni kvadratga qayta joylashtirish. Asosiy harakatni tomosha qiling:"},
                            {type: "diagram", html: `<div class="babyl-diagram">
  <div class="babyl-stage">
    <div class="babyl-label">x ga (x+10) to'rtburchak</div>
    <div class="babyl-rect">x · (x+10)<br>= 24</div>
  </div>
  <div class="babyl-arrow">→</div>
  <div class="babyl-stage">
    <div class="babyl-label">Yarmini (5) ostiga yopishtiring</div>
    <div class="babyl-grid">
      <div>x · x</div><div>5 · x</div>
      <div style="border-top:1.5px solid rgba(99,184,255,0.5)"></div><div>5 · x</div>
    </div>
  </div>
  <div class="babyl-arrow">→</div>
  <div class="babyl-stage">
    <div class="babyl-label">Deyarli kvadrat</div>
    <div class="babyl-grid">
      <div>x²</div><div>5x</div>
      <div>5x</div><div class="highlight">??<br><small>5²=25</small></div>
    </div>
  </div>
</div>`},
                            {type: "p", text: "Keyin ular yetishmayotgan burchakni (maydoni 5² = 25) to'ldirish uchun kvadratni to'ldirdilar, (x + 5) tomonli va maydoni 24 + 25 = 49 bo'lgan to'liq kvadrat berdi. Chunki 49 = 7², tomon (x + 5) = 7, shuning uchun x = 2. Siz zamonaviy algebra bilan olgan xuddi shu javob, to'liq rasmlar bilan olingan."},
                            {type: "p", text: "\"Kvadrat\" so'zi lotincha quadratus = \"kvadratlangan\" dan keladi — chunki Bobilliklar uchun bu haqiqatan ham yer kvadratlari haqida edi."}
                        ]
                    },
                    {
                        blocks: [
                            {type: "p", text: "Mil. ~820, Bag'dod. Al-Xorazmiy nomli fors matematik al-jabr (\"tiklash\") nomli kitob yozadi. Bu kitob zamonaviy matematikaga uchta asosiy narsa beradi:"},
                            {type: "ul", items: [
                                "Algebra so'zi (al-jabrdan)",
                                "Algoritm so'zi (uning ismining lotinlashtirilgan shaklidan)",
                                "Har bir muammo ushbu turga mos keladi — ax² + bx + c = 0 — va bitta tizimli usul ularning hammasini yecha oladi degan tushuncha"
                            ]},
                            {type: "p", text: "Al-Xorazmiydan oldin, har bir muammo o'zining geometrik hiylasini talab qildi. Undan keyin, bitta jarayon ularning hammasini boshqardi."},
                            {type: "p", text: "Bugun. Xuddi shu tenglama, zamonaviy belgilanish, butun dunyoda o'qitiladi. Siz bu asbobni yer o'lchash, o'qni nishonga qo'yish, arka qurish va raketa uchirish uchun 4000 yillik insonlar zanjirining oxirgi bo'g'chisiz."},
                            {type: "p", text: "<strong>Sodda so'zlar bilan:</strong><br>Odamlar 4000 yil davomida kvadratlarni yechishgan. Bobilliklar ularni loy ustida kvadratlar sifatida chizishgan. Bag'doddan Al-Xorazmiy ularni birinchi marta tizimli ravishda ko'rib chiqqan — va uning kitobi bizga \"algebra\" so'zini berdi. Siz piramidalarni qurgan xuddi shu matematikani o'rganmoqdasiz."}
                        ]
                    }
                ]
            },
            {
                id: 4,
                title: "PANEL 4 — HAYOTDA QO'LLASH",
                pages: [
                    {
                        blocks: [
                            {type: "p", text: "Kvadratlar faqat uy vazifasi matematikasi emas. Ular deyarli hamma narsada, egri chiziqda harakatlanadigan yoki kvadratga bog'liq bo'lgan hamma narsada ishlaydi."},
                            {type: "h2", text: "🏀 Basketbol zarbasi"},
                            {type: "p", text: "Chiqarilgandan keyin t soniyada to'pning balandligi:"},
                            {type: "quote", text: "h(t) = v₀·t – ½·g·t²"},
                            {type: "p", text: "bunda v₀ chiqarish tezligi va g ≈ 9.8 m/s² gravitatsiya. Bu t bo'yicha kvadrat. \"To'p qachon halqaga yetadi?\" yoki \"Eng yuqori balandlik qancha?\" kabi savollar bu kvadratni t uchun yechishga olib keladi. Har bir basketbol video o'yinidagi har bir fizika dvigateli uni har kadrda yechadi."},
                            {type: "code", text: "      cho'qqi ✦\n          ╱ ╲\n         ╱   ╲\n        ╱     ╲\n       ╱       ╲\n      ╱         ✦ halqa\n    ─●─────────────── yer\n    chiqarish"}
                        ]
                    },
                    {
                        blocks: [
                            {type: "h2", text: "🚗 To'xtash masofasi"},
                            {type: "p", text: "Yo'ldagi mashinangizning to'xtash masofasi:"},
                            {type: "quote", text: "d = v² / (2·μ·g)"},
                            {type: "p", text: "Masofa tezlikning kvadrati bilan o'sadi. Tezlikni ikki baravar oshiring → to'xtash masofasi 4 baravar. Uch baravar oshiring → 9 baravar. Shuning uchun avtomagistral tezlik chegaralari qat'iy va 120 km/soat da xavfsizlik masofasini buzish haqiqatan xavfli."},
                            {type: "code", text: "  tezlik     to'xtash masofasi\n  30 km/soat  ▓▓                            ~5 m\n  60 km/soat  ▓▓▓▓▓▓▓▓                     ~20 m   (2× emas 4×)\n  90 km/soat  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓           ~45 m   (3× emas 9×)\n  120 km/soat ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ~80 m   (4× emas 16×)"},
                            {type: "p", text: "Bu v² amalda kvadrat munosabat."},
                            {type: "h2", text: "📡 Sun'iy yo'ldosh idishlari, faralar, teleskoplar"},
                            {type: "p", text: "Hammasi parabolalar shaklida — y = x² grafigi. Parabolalar go'zal geometrik xususiyatga ega: o'qqa parallel kelgan har qanday nur bitta fokus nuqtasiga qaytadi. Shuning uchun televizor idishi kuchsiz signalni jamlaydi, avtomobil farasi kichik lampadan zich nur hosil qiladi va teleskop uzoq yulduz nurini fokuslaydi. Bu egri chiziq so'zma-so'z kvadrat tenglamaning rasmi."},
                            {type: "code", text: "            parallel nur kiradi\n            ↓   ↓   ↓   ↓   ↓\n           ╲    │   │   │    ╱\n            ╲   │   │   │   ╱\n             ╲  │   │   │  ╱\n              ╲ │   │   │ ╱\n               ╲│   │   │╱\n                ● ← hammasi fokus nuqtasida jamlanadi"}
                        ]
                    },
                    {
                        blocks: [
                            {type: "h2", text: "💰 Biznes va daromad"},
                            {type: "p", text: "Chipta narxi va umumiy daromad. Narxni juda past qo'ying → to'la zal lekin o'rindoshga past daromad. Juda yuqori qo'ying → bo'sh zal. O'rtada daromad cho'qqiga chiqadigan shirin nuqta bor. Daromad = narx × tashrif buyuruvchilar munosabati odatda kvadratga keladi va shirin nuqtani topish uni yechishni anglatadi."},
                            {type: "h2", text: "🌉 Ko'priklar"},
                            {type: "p", text: "Osmondagi ko'prik kabellar parabola shaklida osiladi. Muhandislar kvadratlarni yechish orqali kabellarni o'lchaydi, har bir tirgakdagi kuchlanishni hisoblaydi va ko'prikning qulamayishini tasdiqlaydi. Dunyodagi har bir osmon ko'prigi — Bruklin ko'prigi, Golden Gate, Akashi Kaikyo — ushbu matematika bilan ishlab chiqilgan."},
                            {type: "p", text: "Ushbu misollarning har biri siz endi egallayotgan xuddi shu tenglamadan foydalanadi."},
                            {type: "p", text: "<strong>Sodda so'zlar bilan:</strong><br>Otgan to'p → kvadrat. To'xtagan mashina → kvadrat. Sun'iy yo'ldosh idishi → kvadrat. Qulamaydigan ko'prik → kvadrat. Haqiqiy dunyodagi ko'pchilik egri chiziqlarning ichida kvadrat tenglama yashiringan."}
                        ]
                    }
                ]
            },
            {
                id: 5,
                title: "PANEL 5 — NEGA SIZGA SHAXSAN BU KERAK",
                pages: [
                    {
                        blocks: [
                            {type: "p", text: "Uch joyda siz bu tenglama bilan yana uchrashasiz, kafolat:"},
                            {type: "p", text: "① Fizika (9-11-sinf). Har bir otilma muammosi kvadrat. Balandlikdan ob'ektni tashlang — ½gt² tenglamada. Toshni yuqoriga otib yuboring → kvadrat. Har qanday burchakda narsa ishga tushiring → kvadrat. \"Qachon yerga tushadi?\" yoki \"Qancha uzoqqa boradi?\" topish kvadratni yechishni anglatadi. Fizika darsi 10-sinfga kelib reflektor ravishda ko'paytuvchilarga ajrata olmasangiz haqiqatan og'riqli bo'ladi."},
                            {type: "p", text: "② Kirish imtihonlari (DTM, universitet qabuli, Olimpiadalar). Kvadratlar har bir jiddiy o'zbek va xalqaro matematika imtihonida eng ko'p sinovdan o'tkazilgan algebra mavzularidan biri. Ular ayniqsa qiyin emasligi uchun emas — bitta ixcham kvadrat savoli sizning algebrangiz, arifmetikangiz va mantiqiy fikrlashingizni bir vaqtning o'zida sinaydi. Ularni egallagan o'quvchilar oson ballar yig'adi; egallamaganlar xuddi shu oson ballarni yo'qotadi."},
                            {type: "p", text: "③ Egri chiziqlar yoki optimallashtirish bilan bog'liq har qanday narsa — dasturlash, o'yin rivojlantirish, muhandislik, moliya, iqtisod. O'yinlarda to'qnashuvni aniqlash, animatsiya yumshatish, biznes modelida foyda optimallashtirish, linza dizayni, antenna dizayni, foiz va o'sish egri chiziqlari — hammasi o'zida kvadrat. Agar siz hech qachon o'yin yaratmoqchi, biznes modelini yaratmoqchi, mahsulot ishlab chiqmoqchi yoki ma'lumotlarni tahlil qilmoqchi bo'lsangiz, bu tenglama asosiy talab."},
                            {type: "p", text: "Bir haftada ushbu bo'limni egallang va siz o'rta maktab matematikasining yarmida paydo bo'ladigan va keyingi o'n yil davomida foydali bo'ladigan asbobni ochdingiz."},
                            {type: "p", text: "<strong>Sodda so'zlar bilan:</strong><br>Siz fizikada bunga yana duch kelasiz. Katta imtihonlaringizda ko'rasiz. Agar dasturlash, biznes boshqarish yoki haqiqiy narsa qurishni xohlasangiz, ko'rasiz. Bir hafta hozir keyinchalik yillar chalkashlikdan saqlaydi."}
                        ]
                    }
                ]
            }
        ];

        // ── Wave V.1 (preview pagination 2026-04-30) ─────────────────────
        // Long authored pages used to scroll into a long article that didn't
        // fit the panel-card and left awkward blank space below the action
        // button. Split each authored page into multiple rendered pages
        // sized so the active page only needs ~1-2cm of scroll at most.
        //
        // The estimate is intentionally rough — exact pixel measurement
        // depends on font metrics, KaTeX layout, and image natural size
        // none of which are stable until paint. A character-count proxy
        // is good enough to keep most pages within the budget without
        // reflowing forever; the panel-card max-height + overflow-hint
        // (PR #68) handles the remainder.
        const PREVIEW_PAGE_BUDGET_PX = 760;
        function _previewEstimateBlockHeight(b) {
            if (!b || !b.type) return 0;
            // Block-level media: capped at 56vh (~360px on a 640px viewport)
            // by .block-image img / .block-svg svg, plus margin.
            if (b.type === 'image' || b.type === 'svg' || b.type === 'diagram') {
                return 380;
            }
            const text = String(b.text || '');
            // Roughly 50 chars per visible line at the panel width.
            const lines = (s, perLine) => Math.max(1, Math.ceil(s.length / perLine));
            if (b.type === 'h2') {
                return 56 + lines(text, 32) * 32;
            }
            if (b.type === 'code') {
                return 36 + lines(text, 56) * 22;
            }
            if (b.type === 'ul' || b.type === 'ol') {
                const items = Array.isArray(b.items) ? b.items : [];
                return 8 + items.reduce((s, it) => s + 24 + lines(String(it || ''), 50) * 22, 0);
            }
            if (b.type === 'quote' || b.type === 'callout') {
                return 28 + lines(text, 46) * 26;
            }
            // p (default)
            return 22 + lines(text, 50) * 24;
        }
        function _previewChunkPageBlocks(blocks, budget) {
            // Return an array of block-arrays, each estimated to fit within
            // `budget`. Blocks are kept in source order; never split a single
            // block. If a single block alone exceeds the budget (a huge
            // image, say), it's allowed onto its own page so we don't drop
            // it. Caller-empty pages return [[]] so the panel still has at
            // least one page to render.
            const out = [];
            let current = [];
            let acc = 0;
            for (const b of (Array.isArray(blocks) ? blocks : [])) {
                const h = _previewEstimateBlockHeight(b);
                if (acc + h > budget && current.length > 0) {
                    out.push(current);
                    current = [];
                    acc = 0;
                }
                current.push(b);
                acc += h;
            }
            if (current.length) out.push(current);
            // Bug #4 post-pass: merge metadata-only sub-page or too-short
            // trailing chunks into the previous page so the student never
            // lands on a panel containing just `[Bloom: L3 | PISA: L3]` or
            // a similarly tiny tag-line. Only the FIRST page is exempt
            // (no previous page to merge into).
            return _previewMergeMetadataOnlyPages(out.length ? out : [[]]);
        }

        // Post-pass for the preview chunker — merge metadata-only sub-page
        // and too-short pages into their predecessor. "Metadata-only" means
        // a page whose visible text matches a tag-line regex like
        // `[Bloom: L3 | PISA: L3]`. "Too-short" means the page renders fewer
        // than ~80 visible characters and is not the first page of the panel.
        function _previewMergeMetadataOnlyPages(pages) {
            if (!Array.isArray(pages) || pages.length <= 1) return pages;
            const TAG_LINE_RE = /^\[(?:Bloom|PISA|Damage|Tag|Tags)\b[^\]]*\]\s*$/i;
            const SHORT_PAGE_THRESHOLD = 80;
            const visibleText = (block) => {
                if (!block || !block.type) return '';
                if (block.type === 'ul' || block.type === 'ol') {
                    return (Array.isArray(block.items) ? block.items : [])
                        .map(it => String(it || '').replace(/<[^>]+>/g, '').trim())
                        .join(' ').trim();
                }
                if (block.type === 'image' || block.type === 'svg' || block.type === 'diagram') {
                    // Visual blocks aren't metadata-only — keep them on their own page.
                    return 'X'.repeat(SHORT_PAGE_THRESHOLD + 1);
                }
                return String(block.text || '').replace(/<[^>]+>/g, '').trim();
            };
            const pageText = (blocks) => (blocks || [])
                .map(visibleText).join(' ').trim();
            const isMetadataOnly = (blocks) => {
                if (!Array.isArray(blocks) || blocks.length === 0) return true;
                // All non-empty blocks must be tag-line text.
                const lines = blocks
                    .map(visibleText)
                    .filter(s => s.length > 0);
                if (lines.length === 0) return true;
                return lines.every(line => TAG_LINE_RE.test(line));
            };
            const merged = [pages[0]];
            for (let i = 1; i < pages.length; i++) {
                const prev = merged[merged.length - 1];
                const curBlocks = pages[i] || [];
                const visibleLen = pageText(curBlocks).length;
                if (isMetadataOnly(curBlocks) || visibleLen < SHORT_PAGE_THRESHOLD) {
                    // Merge into previous page (mutate prev in place to keep
                    // the same array identity, since callers iterate it).
                    for (const blk of curBlocks) prev.push(blk);
                } else {
                    merged.push(curBlocks);
                }
            }
            return merged;
        }
        function _previewExpandPanelPages(panel, budget) {
            const expanded = [];
            const sourcePages = Array.isArray(panel && panel.pages) ? panel.pages : [];
            for (const page of sourcePages) {
                const chunks = _previewChunkPageBlocks(page && page.blocks, budget);
                for (const chunk of chunks) expanded.push({ blocks: chunk });
            }
            return Object.assign({}, panel, { pages: expanded.length ? expanded : [{ blocks: [] }] });
        }
        // Apply chunking once at script init so renderPanel / nextPanel /
        // prevPanel / swipe / dot count all see the same expanded pages.
        // Exposed on window for the test harness to drive directly.
        for (let i = 0; i < PANELS.length; i++) {
            PANELS[i] = _previewExpandPanelPages(PANELS[i], PREVIEW_PAGE_BUDGET_PX);
        }
        window._previewChunkPageBlocks = _previewChunkPageBlocks;
        window._previewEstimateBlockHeight = _previewEstimateBlockHeight;
        window._previewExpandPanelPages = _previewExpandPanelPages;
        window.PREVIEW_PAGE_BUDGET_PX = PREVIEW_PAGE_BUDGET_PX;

        // QUOTES is replaced by server/services/injector.py at render time with
        // a three-slot sequence from server/services/quotes.py:
        // [0] opening gate quote, [1] first-third quote/fact mix,
        // [2] post-flashcard fact. The empty default below is only ever seen
        // if injection is bypassed during dev.
        const QUOTES = [];

        const FLASHCARDS = [
            {
                cluster: "NAMES",
                front: { term: "KVADRAT TENGLAMA", formula: "ax² + bx + c = 0" },
                back: {
                    definition: "Noma'lumning kvadratda uchragan tenglama. Standart shakl: ax² + bx + c = 0, bunda a ≠ 0.",
                    bullets: null,
                    hook: "\"kvadrat\" so'zi lotincha quadratus = \"kvadratlangan\" dan keladi — Bobilliklar bu tenglamalarni so'zma-so'z kvadratlar chizib yechishgan."
                }
            },
            {
                cluster: "NAMES",
                front: { term: "KVADRAT TENGLAMANING QISMLARI", formula: null },
                back: {
                    definition: "a = bosh koeffitsiyent (yetakchi) — x² oldidagi son\nb = ikkinchi koeffitsiyent (o'rta) — x oldidagi son\nc = ozod had (erkin had / konstanta) — yolg'iz turgan son, x bog'liq emas",
                    bullets: null,
                    hook: "\"ozod\" erkin degani — erkin hadni x zanjirlab qo'ymaydi."
                }
            },
            {
                cluster: "NAMES",
                front: { term: "ILDIZ  (root)", formula: null },
                back: {
                    definition: "x ning tenglamani to'g'ri qiladigan qiymati. Agar uni qo'ysangiz, ikkala tomon mos keladi.",
                    bullets: ["2 ta ildiz   (eng keng tarqalgan)", "1 ta ildiz   (maxsus holat)", "0 ta ildiz   (haqiqiy yechim yo'q)"],
                    hook: "\"ildiz\" = ildiz (o'simlik ildizi kabi). Yechim tenglamani nolda \"ildizlaydi\"."
                }
            },
            {
                cluster: "NAMES",
                front: { term: "ARIFMETIK KVADRAT ILDIZ", formula: "√d" },
                back: {
                    definition: "Konventsiya bo'yicha, √d faqat MUSBAT ildizni anglatadi.\n√25 = 5    EMAS ±5\n√64 = 8    EMAS ±8\nManfiy ildiz, kerak bo'lganda, –√d sifatida yoziladi.",
                    bullets: null,
                    hook: "√ belgisi va'da — \"sizga musbatnigina beraman, boshqa narsa emas.\""
                }
            },
            {
                cluster: "FORMULAS",
                front: { term: "KVADRAT TENGLAMA · STANDART SHAKL", formula: null },
                back: {
                    definition: "ax² + bx + c = 0\na, b, c ∈ ℝ\na ≠ 0",
                    bullets: null,
                    hook: "a ≠ 0 juda muhim — agar a = 0 bo'lsa, x² yo'qoladi va bu faqat chiziqli tenglama bo'ladi, kvadrat emas."
                }
            },
            {
                cluster: "FORMULAS",
                front: { term: "SODDA HOLAT", formula: "x² = d   →   x = ?" },
                back: {
                    definition: "x₁,₂ = ±√d    (d ≥ 0 bo'lganda)",
                    bullets: ["d > 0  →  ikki ildiz", "d = 0  →  bitta ildiz", "d < 0  →  haqiqiy ildiz yo'q"],
                    hook: "parabola y = x² gorizontal d chizig'ini 2, 1 yoki 0 joyda kesadi."
                }
            },
            {
                cluster: "FORMULAS",
                front: { term: "KVADRATLAR AYIRMASI", formula: "a² – b² = ?" },
                back: {
                    definition: "a² – b² = (a – b)(a + b)\nQuyidagilarni ko'paytuvchilarga ajratishda ishlatiladi:\nx² – 64 = (x – 8)(x + 8)\nx² – d  = (x – √d)(x + √d)",
                    bullets: null,
                    hook: "ikki kvadrat orasida bitta minus belgisi — har doim yig'indi × ayirma ko'rinishida ajraladi."
                }
            },
            {
                cluster: "FORMULAS",
                front: { term: "KO'PAYTUVCHILARGA AJRATISH ANDOZASI", formula: "x² + bx + c = ( ? )( ? )" },
                back: {
                    definition: "Quyidagi shartlarni qanoatlantiruvchi p, q sonlarini toping:\np + q  =  b   (o'rta koeffitsient)\np · q  =  c   (ozod had)\nKeyin:\nx² + bx + c = (x + p)(x + q)",
                    bullets: null,
                    hook: "\"yig'indi = o'rta, ko'paytma = oxirgi.\" Ko'paytuvchi juftlarining qisqa jadvalini tuzing, to'g'ri juft yagona."
                }
            },
            {
                cluster: "DECISIONS",
                front: { term: "QAYSI USULNI TANLASH?", formula: null },
                back: {
                    definition: "Tenglama quyidagicha ko'rinadi…  →  Foydalaning…",
                    bullets: ["x² = d  (2 ta had)  →  ikkala tomondan kvadrat ildiz", "ax² + bx + c = 0  (3 ta had)  →  ko'paytuvchilarga ajratish, yoki kvadrat tenglama formulasi"],
                    hook: "ikki had → √. Uch had → (  )(  )."
                }
            },
            {
                cluster: "DECISIONS",
                front: { term: "x² = d  nechta ildiz?", formula: null },
                back: {
                    definition: "d > 0   →  2 ta haqiqiy ildiz   ( x = ±√d )\nd = 0   →  1 ta ildiz           ( x = 0 )\nd < 0   →  0 ta haqiqiy ildiz   (bo'sh)",
                    bullets: null,
                    hook: "haqiqiy sonning kvadrati hech qachon manfiy bo'lmaydi, shuning uchun d < 0 ning haqiqiy javobi yo'q."
                }
            },
            {
                cluster: "KEY INSIGHTS",
                front: { term: "IKKI JAVOB, BIR HAQIQAT", formula: null },
                back: {
                    definition: "Kvadrat tenglamalar odatda IKKI matematik yechim beradi. Tenglama kontekstni bilmaydi. Siz haqiqiy dunyo qoidalari bo'yicha filtrlaysiz:",
                    bullets: ["uzunliklar manfiy bo'lishi mumkin emas", "vaqt manfiy bo'lishi mumkin emas", "sonlar butun bo'lishi kerak"],
                    hook: "ikkala javob ham matematik jihatdan to'g'ri — biri fizik jihatdan mumkin emas. Bu xato emas, balki xususiyat."
                }
            },
            {
                cluster: "KEY INSIGHTS",
                front: { term: "±   (plyus-minus)", formula: null },
                back: {
                    definition: "\"Shu sonning musbat VA manfiy versiyasi\" degan qisqacha yozilish.\nx = ±5    degani    x = 5  YOKI  x = –5\nx₁,₂ = ±√d   ikkala ildizni bitta qatorda jamlaydi",
                    bullets: null,
                    hook: "bitta belgi, ikki javob. Muammoni yechayotganda IKKISINI ham sanab o'tishni unutmang."
                }
            }
        ];

        let state = {
            stage: 0,
            panelIndex: 0,
            pageIndex: 0,
            cardIndex: 0,
            cardFlipped: false,
            hintShown: false,
            isAnimating: false,
            // Bug #6: in-flight flashcard horizontal-switch guard. switchCard
            // sets this to true on entry and clears it after the transition
            // settles (transitionend OR 420ms safety fallback).
            cardSwitching: false,
            touchStart: null
        };

        // DOM Elements
        let btn, btnText;

        function init() {
            btn = document.getElementById('action-button');
            btnText = btn ? btn.querySelector('.btn-text') : null;

            if (btn) {
                btn.addEventListener('click', handleAction);
            }

            document.querySelectorAll('.ms-option-btn').forEach((b, i) => {
                b.addEventListener('click', () => msHandleAnswer(i));
            });

            // UNIFIED POINTER SWIPE — touch + mouse, skip on long edge drag
            const SKIP_SHOW = 100;
            const SKIP_GO   = 210;
            const EDGE_ZONE = 48;
            const MIN_AXIS  = 8;   // px total movement before committing to an axis
            let swipe = { active: false, startX: 0, startY: 0, locked: false, scrollable: false, fromEdge: false };

            const skipOverlay = document.getElementById('skip-overlay');
            const skipPill    = document.getElementById('skip-pill');

            function resetDragPreview() {
                const ap = document.querySelector('#panel-content .page.active');
                if (ap && ap.style.transform) {
                    ap.style.transition = 'transform 320ms cubic-bezier(0.34, 1.56, 0.64, 1)';
                    ap.style.transform = '';
                    setTimeout(() => { if (ap) ap.style.transition = ''; }, 340);
                }
                if (skipOverlay) skipOverlay.classList.remove('visible');
                if (skipPill)    skipPill.classList.remove('skip-ready');
            }

            document.addEventListener('pointerdown', e => {
                if (!e.isPrimary || e.button !== 0) return;
                if (state.stage === 7.5) return;
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
                const fromEdge = e.clientX <= EDGE_ZONE || e.clientX >= window.innerWidth - EDGE_ZONE;
                // In game-break stage AND on the Consolidation / Reflection
                // interstitial screens (stage 6.5 / 7.7), only track edge drags
                // (skip gesture) — let internal content scroll/interact freely.
                // Reading (4.7) DOES allow within-phase horizontal swipe-left to
                // advance between segment + checkpoint panels.
                // Stage 5 (Game Breaks) + Reflection (7.7) accept ONLY edge
                // drags (skip gesture) so internal content can scroll/interact
                // freely. Reading (4.7) and Consolidation (6.5) DO allow
                // within-phase horizontal swipes — both run the wave2 slide
                // stream and dispatch into wave2SlideNavigate below.
                const isInterstitialNoSwipe = state.stage === 7.7;
                if ((state.stage === 5 || isInterstitialNoSwipe) && !fromEdge) return;
                // Detect horizontally scrollable ancestor — if found, skip swipe handling
                // (horizontal swipe only blocked by horizontally-scrolling content; vertical
                // scroll containers don't conflict with horizontal page-swipe gestures).
                let scrollable = false;
                let node = e.target;
                while (node && node !== document.body) {
                    const ox = window.getComputedStyle(node).overflowX;
                    if ((ox === 'auto' || ox === 'scroll') && node.scrollWidth > node.clientWidth + 2) { scrollable = true; break; }
                    if ((node.tagName === 'CODE' || node.tagName === 'PRE') && node.scrollWidth > node.clientWidth) { scrollable = true; break; }
                    node = node.parentNode;
                }
                swipe = { active: true, startX: e.clientX, startY: e.clientY, locked: false, scrollable, fromEdge };
            }, { passive: true });

            document.addEventListener('pointermove', e => {
                if (!swipe.active || !e.isPrimary) return;
                const dx = e.clientX - swipe.startX;
                const dy = e.clientY - swipe.startY;
                const absDx = Math.abs(dx);
                const absDy = Math.abs(dy);
                // Wait for enough movement before deciding horizontal vs vertical
                if (!swipe.locked && absDx + absDy < MIN_AXIS) return;
                // Commit axis — vertical or scrollable cancels the swipe
                if (!swipe.locked) {
                    if (absDy >= absDx || swipe.scrollable) { swipe.active = false; resetDragPreview(); return; }
                    swipe.locked = true;
                }
                if (state.isAnimating) return;
                // Panel drag preview — only if panel has multiple pages
                if (state.stage === 2 && PANELS[state.panelIndex].pages.length > 1) {
                    const ap = document.querySelector('#panel-content .page.active');
                    if (ap) { ap.style.transition = 'none'; ap.style.transform = `translateX(${dx * 0.55}px)`; }
                }
                // Skip overlay — edge drags only
                if (swipe.fromEdge && absDx >= SKIP_SHOW) {
                    if (skipOverlay) skipOverlay.classList.add('visible');
                    if (skipPill)    skipPill.classList.toggle('skip-ready', absDx >= SKIP_GO);
                } else {
                    if (skipOverlay) skipOverlay.classList.remove('visible');
                    if (skipPill)    skipPill.classList.remove('skip-ready');
                }
            }, { passive: true });

            document.addEventListener('pointerup', e => {
                if (!swipe.active || !e.isPrimary) return;
                const { startX, startY, scrollable, fromEdge } = swipe;
                swipe.active = false;
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;
                const absDx = Math.abs(dx);
                if (skipOverlay) skipOverlay.classList.remove('visible');
                if (skipPill)    skipPill.classList.remove('skip-ready');
                if (scrollable || state.isAnimating) { resetDragPreview(); return; }
                if (absDx > Math.abs(dy)) {
                    if (fromEdge && absDx >= SKIP_GO) {
                        const ap = document.querySelector('#panel-content .page.active');
                        if (ap) { ap.style.transition = ''; ap.style.transform = ''; }
                        skipCurrentPhase();
                    } else if (absDx > 50 && (state.stage === 2 || state.stage === 3)) {
                        const dir = dx > 0 ? 'right' : 'left';
                        const p = state.stage === 2 ? PANELS[state.panelIndex] : null;
                        const willNavigate = state.stage === 3 || (
                            (dir === 'left'  && state.pageIndex < p.pages.length - 1) ||
                            (dir === 'right' && (state.pageIndex > 0 || state.panelIndex > 0))
                        );
                        if (willNavigate) {
                            const ap = document.querySelector('#panel-content .page.active');
                            if (ap) ap.style.transition = '';
                            handleSwipe(dir);
                        } else {
                            resetDragPreview();
                        }
                    } else if (absDx > 50 && state.stage === 4.7) {
                        // Reading: dispatch into the wave2 slide stream. The
                        // helper's canAdvance hook gates forward swipes when
                        // the current panel is an unanswered question; back
                        // swipes are always allowed.
                        const dir = dx > 0 ? -1 : +1;
                        wave2SlideNavigate('reading-stream', dir);
                        resetDragPreview();
                    } else if (absDx > 50 && state.stage === 6.5) {
                        // Consolidation: dispatch into the wave2 slide stream.
                        // Not graded — canAdvance returns true always; swipe
                        // past the last panel calls onExitForward.
                        const dir = dx > 0 ? -1 : +1;
                        wave2SlideNavigate('cons-stream', dir);
                        resetDragPreview();
                    } else {
                        resetDragPreview();
                    }
                } else {
                    resetDragPreview();
                }
            });

            document.addEventListener('pointercancel', e => {
                if (!e.isPrimary) return;
                swipe.active = false;
                resetDragPreview();
            });
        }

        function handleAction() {
            if (state.isAnimating) return;
            // Real-Life: block "Keyingi" while the AI tutor is still grading
            // the open-ended response so students can't bypass the verdict.
            if (btn && btn.classList.contains('is-ai-pending')) return;
            if (state.stage === 0) startStage1();
            else if (state.stage === 1 && btn.classList.contains('state-pill')) startStage2();
            else if (state.stage === 2) {
                // NAV-01 + NAV-02 (2026-05-06): on intermediate pages, advance one
                // page; on the last page of a panel, advance to the next panel.
                // Mirrors the swipe-left direction so click + swipe stay consistent.
                const p = PANELS[state.panelIndex];
                if (p && state.pageIndex < p.pages.length - 1) {
                    switchPage(state.pageIndex + 1);
                } else {
                    nextPanel();
                }
            }
            else if (state.stage === 2.5 && btn.classList.contains('state-pill')) startStage3();
            else if (state.stage === 3) endStage3();
            else if (state.stage === 3.5 && btn.classList.contains('state-pill')) {
                const breakScreen = document.getElementById('screen-break');
                if (breakScreen) breakScreen.classList.remove('active');
                startMemorySprintPhase();
            }
            else if (state.stage === 4.5 && btn.classList.contains('state-pill')) {
                const screenMs = document.getElementById('screen-ms');
                if (screenMs) screenMs.classList.remove('active');
                // Wave 2: Reading (Til pipeline) → Listening, both before Game
                // Breaks. Each auto-skips when its own content is empty.
                const afterReading = () => {
                    if (typeof showListeningScreen === 'function' && listeningHasContent()) {
                        showListeningScreen(startStage5);
                    } else {
                        startStage5();
                    }
                };
                if (typeof showReadingScreen === 'function' && readingHasContent()) {
                    showReadingScreen(afterReading);
                } else {
                    afterReading();
                }
            }
            else if (state.stage === 5) gbHandleAction();
            else if (state.stage === 6 && RLC_CASE && rlcHandleAction) rlcHandleAction();
            else if (state.stage === 6) rlHandleAction();
            else if (state.stage === 7) bossHandleAction();
            else if (state.stage === 7.5 && btn.classList.contains('state-pill')) {
                // Wave 2 + grading-flow update: regardless of whether the Boss
                // was defeated or survived, the next click always advances to
                // the AMR Results scorecard. The decision to redo the homework
                // is moved INTO the results screen (a button is shown there
                // when the session score is < 60%).
                const showResultsThenFinish = () => {
                    if (typeof showResultsScreen === 'function') {
                        showResultsScreen();
                    } else {
                        // Defensive — if for any reason showResultsScreen wasn't
                        // injected, fall through to plain finish.
                        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
                    }
                    btn.classList.remove('pulse', 'state-pill');
                    btn.classList.add('state-line');
                    if (btnText) btnText.style.opacity = '0';
                };
                // Ungraded Extra Materials show after the Boss, just before the
                // Reflection + Results. Auto-skips when no items are authored.
                const afterExtras = () => {
                    if (typeof showReflectionScreen === 'function' && reflectionHasContent()) {
                        showReflectionScreen(showResultsThenFinish);
                    } else {
                        showResultsThenFinish();
                    }
                };
                if (typeof showExtraMaterialsScreen === 'function' && extraMaterialsHasContent()) {
                    showExtraMaterialsScreen(afterExtras);
                } else {
                    afterExtras();
                }
            }
        }

        // ── STAGE SETTER (auto-updates progress bar) ────────────
        function setStage(n) {
            state.stage = n;
            updatePhaseProgress();
            // Wave F2: notify the persistent tutor widget so its phase badge updates.
            // Stage→phase mapping:
            //   0, 1, 2 (panel preview)        → preview
            //   2.5–6.5 (any practice activity) → practice
            //   7, 7.5  (boss + boss-done)      → boss
            //   7.7+    (reflection / done)     → preview (open Q&A)
            try {
                let phaseName = 'preview';
                if (n >= 7 && n < 7.7) phaseName = 'boss';
                else if (n > 2 && n < 7) phaseName = 'practice';
                else phaseName = 'preview';
                document.dispatchEvent(new CustomEvent('nets:phase-change', {
                    detail: { phase: phaseName, stage: n, questionId: null }
                }));
            } catch (e) { /* widget optional */ }
        }

        // ── PHASE PROGRESS BAR ──────────────────────────────────
        // Dots (1..7) map to phases as before:
        //   1 = Preview (gate quote + reading panels)
        //   2 = Flashcards
        //   3 = Memory Sprint
        //   4 = Game Breaks (incl. Adaptive Quiz & the Reading interstitial)
        //   5 = Real Life
        //   6 = Boss (incl. Consolidation interstitial)
        //   7 = Done (Reflection + Results)
        //
        // PROGRESS IS DRIVEN BY REAL COMPLETION, NOT RAW state.stage.
        //
        // Each phase carries {viewed, required, complete}. `viewed` increments
        // when the student does an action that counts toward this phase
        // (advanced a panel, answered a sprint question, finished a sub-game,
        // answered a boss question, etc.). `complete` is the authoritative
        // "phase fully done" flag — it is set ONLY when the runtime crosses
        // the phase's terminal action (last panel viewed, last flashcard
        // done, sprint finished, results shown).
        //
        // updateProgress() reads completionState — not state.stage — to set
        // each segment's done/active class and inline width. The active dot
        // partial-fills proportionally (8% floor visible-but-just-started,
        // 92% ceiling so it can never read as "done" until `complete` flips).
        const _phaseDotById = {
            preview: 1, flashcards: 2, sprint: 3, gameBreaks: 4,
            realLife: 5, boss: 6, done: 7,
        };
        // Stage → "currently inside this phase" so the active dot reflects
        // where the student is right now. Half-step interstitials map to the
        // phase they belong to (Reading→gameBreaks, Consolidation→boss,
        // Reflection→done). Stage 8 = results screen → all phases done.
        const _phaseIdByStage = {
            0: null, 1: 'preview', 2: 'preview',
            2.5: 'flashcards', 3: 'flashcards',
            3.5: 'sprint', 4: 'sprint', 4.5: 'sprint',
            4.7: 'gameBreaks', 5: 'gameBreaks',
            6: 'realLife',
            6.5: 'boss', 7: 'boss',
            7.5: 'done', 7.7: 'done', 8: 'done',
        };
        // Back-compat: external code (Wave 2 comments, screenshots) may
        // reference phaseMap. Keep it as a derived view so anything reading
        // it gets the canonical dot for a given stage.
        const phaseMap = (function buildPhaseMap() {
            const out = {};
            Object.keys(_phaseIdByStage).forEach(stage => {
                const id = _phaseIdByStage[stage];
                out[stage] = id ? (_phaseDotById[id] || 0) : 0;
            });
            return out;
        })();

        const completionState = {
            preview:    { viewed: 0, required: 1, complete: false },
            flashcards: { viewed: 0, required: 1, complete: false },
            sprint:     { viewed: 0, required: 1, complete: false },
            gameBreaks: { viewed: 0, required: 1, complete: false },
            realLife:   { viewed: 0, required: 1, complete: false },
            boss:       { viewed: 0, required: 1, complete: false },
            done:       { viewed: 0, required: 1, complete: false },
        };

        function setPhaseRequired(id, n) {
            const ph = completionState[id];
            if (!ph) return;
            ph.required = Math.max(1, parseInt(n, 10) || 1);
            if (ph.viewed > ph.required) ph.viewed = ph.required;
            updateProgress();
        }

        function bumpPhase(id, by) {
            const ph = completionState[id];
            if (!ph) return;
            const inc = (typeof by === 'number') ? by : 1;
            ph.viewed = Math.min(ph.required, ph.viewed + inc);
            updateProgress();
        }

        function setPhaseProgress(id, viewed, required) {
            const ph = completionState[id];
            if (!ph) return;
            if (typeof required === 'number' && required > 0) {
                ph.required = required;
            }
            ph.viewed = Math.max(0, Math.min(ph.required, parseInt(viewed, 10) || 0));
            updateProgress();
        }

        function completePhase(id) {
            const ph = completionState[id];
            if (!ph) return;
            ph.viewed = ph.required;
            ph.complete = true;
            updateProgress();
        }

        function completeAllPhases() {
            Object.keys(completionState).forEach(id => {
                const ph = completionState[id];
                ph.viewed = ph.required;
                ph.complete = true;
            });
            updateProgress();
        }

        function _currentPhaseIdForStage(stage) {
            // Use Object.prototype.hasOwnProperty in case stage is a string key.
            if (Object.prototype.hasOwnProperty.call(_phaseIdByStage, stage)) {
                return _phaseIdByStage[stage];
            }
            // Unknown stage: fall back to numeric-nearest match.
            return null;
        }

        function updateProgress() {
            const bar = document.getElementById('phase-progress');
            if (!bar) return;

            const curId = _currentPhaseIdForStage(state.stage);
            const curDot = curId ? (_phaseDotById[curId] || 0) : 0;

            bar.classList.toggle('visible', curDot > 0);
            // Reflect the active phase index in the progressbar landmark
            // so AT users hear "phase 4 of 7" as the runtime advances.
            bar.setAttribute('aria-valuenow', String(curDot));

            for (let i = 1; i <= 7; i++) {
                const seg = document.getElementById('ps-' + i);
                if (!seg) continue;
                seg.classList.remove('done', 'active');
                const fill = seg.querySelector('.phase-seg-fill');

                // Find the phase id that owns this dot.
                const owner = Object.keys(_phaseDotById).find(k => _phaseDotById[k] === i);
                const ph = owner ? completionState[owner] : null;

                if (ph && ph.complete) {
                    seg.classList.add('done');
                    if (fill) fill.style.width = '100%';
                } else if (i === curDot) {
                    seg.classList.add('active');
                    if (fill) {
                        const ratio = ph
                            ? Math.max(0, Math.min(1, ph.viewed / Math.max(1, ph.required)))
                            : 0;
                        // 8% floor → "started, not yet done"; 92% ceiling →
                        // never reads as full until `complete` flips. Smooth
                        // partial fill in between mirrors real progress.
                        const pct = (8 + ratio * 84).toFixed(2);
                        fill.style.width = pct + '%';
                    }
                } else if (i < curDot) {
                    // Past dot but not explicitly marked complete (e.g. user
                    // skipped via edge-swipe). Treat as done so the bar reads
                    // monotonically forward — but consult the live skip
                    // semantics: a skipped phase whose `viewed > 0` is still
                    // "done" from the bar's perspective.
                    seg.classList.add('done');
                    if (fill) fill.style.width = '100%';
                } else {
                    // Future dot — empty.
                    if (fill) fill.style.width = '0%';
                }
            }
        }

        // Back-compat shim: existing call sites still call updatePhaseProgress().
        function updatePhaseProgress() { updateProgress(); }

        // ── BUTTON TEXT CROSS-FADE ───────────────────────────────
        function setBtnText(text) {
            if (!btnText) return;
            if (btnText.innerText === text) {
                btnText.classList.remove('fade-out', 'fade-in');
                btnText.style.opacity = '1';
                btnText.style.transform = '';
                return;
            }
            btnText.classList.add('fade-out');
            setTimeout(() => {
                btnText.innerText = text;
                btnText.style.opacity = '1';
                btnText.classList.remove('fade-out');
                btnText.classList.add('fade-in');
                setTimeout(() => btnText.classList.remove('fade-in'), 180);
            }, 140);
        }

        function skipCurrentPhase() {
            if (state.isAnimating) return;
            const s = state.stage;
            if (s === 0)   { startStage1(); return; }
            if (s === 1)   { startStage2(); return; }
            if (s === 2)   { showBreakScreen(); return; }
            if (s === 2.5) { startStage3(); return; }
            if (s === 3)   { endStage3(); return; }
            if (s === 4)   { msState.isAnimating = false; msFinishSprint(); return; }
            if (s === 4.5) {
                const screenMs = document.getElementById('screen-ms');
                if (screenMs) screenMs.classList.remove('active');
                startStage5();
                return;
            }
            // Reading (4.7): edge-swipe phase-skip must bypass the checkpoint
            // answer-lock — the user has explicitly asked to leave the phase, so
            // unanswered checkpoints don't gate the exit. Call onContinue with
            // force=true to skip the readingIsComplete() guard inside finishReading.
            if (s === 4.7) {
                if (typeof readingState !== 'undefined' && typeof readingState.onContinue === 'function') {
                    readingState.onContinue(true);
                } else if (typeof btn !== 'undefined' && btn) {
                    btn.click();
                }
                return;
            }
            // Consolidation (6.5) / Reflection (7.7) interstitials — clicking the
            // action button advances them, so edge-swipe-skip just simulates a click.
            if (s === 6.5 || s === 7.7) {
                if (typeof btn !== 'undefined' && btn) btn.click();
                return;
            }
            if (s === 5)   { gbExitToStage6(); return; }
            if (s === 6)   { rlShowEndPlaceholder(); return; }
            if (s === 7)   { bossEnd(false); return; }
        }

        function startStage1() {
            state.isAnimating = true;
            const h1 = document.querySelector('h1');
            const cap = document.querySelector('.caption');
            if(h1) h1.style.opacity = '0';
            if(cap) cap.style.opacity = '0';

            btn.classList.remove('state-start');
            btn.classList.add('state-line');
            setTimeout(() => {
                document.getElementById('screen-0').classList.remove('active');
                document.getElementById('screen-1').classList.add('active');
                setStage(1);
                state.isAnimating = false;
                runQuoteSequence();
            }, 500);
        }

        function runQuoteSequence() {
            const container = document.getElementById('quote-container');
            if (!container) return;
            const presets = ['anim-quote-in-up', 'anim-quote-in-scale', 'anim-quote-in-left'];
            const q = QUOTES[0] || { t: "", a: "", origin: "National", type: "quote" };
            const isGlobal = q.origin === 'Global';
            // Facts are introduced by the "Bilarmidingiz?" pill above the text;
            // quotes are attributed by the author pill below the text. Skip the
            // leading 💡 emoji on facts so the label pill isn't doubled.
            const isFact = q.type !== 'quote';
            const icon = isFact ? '' : '❝';

            const item = document.createElement('div');
            item.className = 'quote-item';

            // Quote line — optional icon prefix, then the quote text as a text
            // node (no innerHTML interpolation, immune to XSS regardless of source).
            const textLine = document.createElement('div');
            textLine.className = 'quote-text-line';
            if (icon) {
                const iconNode = document.createElement('span');
                iconNode.className = 'quote-type-icon';
                iconNode.textContent = icon;
                textLine.appendChild(iconNode);
            }
            textLine.appendChild(document.createTextNode(q.t || ''));

            // Author chip — origin-tinted pill with a dot + author name.
            // Both fact and quote render body first with the label/author chip
            // BELOW it. Uniform layout — no order swap based on type.
            const chipLine = document.createElement('div');
            const chip = document.createElement('span');
            const chipClasses = ['quote-author-chip'];
            if (isGlobal) chipClasses.push('quote-author-chip--global');
            chip.className = chipClasses.join(' ');
            const dot = document.createElement('span');
            dot.className = 'quote-author-chip-dot';
            const authorNode = document.createElement('span');
            const gateLabels = { uz: 'Bilarmidingiz?', ru: 'Знаете ли вы?', en: 'Did you know?' };
            const gateLabel = gateLabels[_runtimeDetectLang()] || gateLabels.uz;
            // Facts use the localized label as the eyebrow (chrome).
            // Quotes show the actual author from data; never reuse the fact label.
            authorNode.textContent = isFact ? gateLabel : (q.a || 'Iqtibos');
            chip.appendChild(dot);
            chip.appendChild(authorNode);
            chipLine.appendChild(chip);

            // Both fact and quote: body first, label/author chip below.
            item.appendChild(textLine);
            item.appendChild(chipLine);

            const preset = presets[Math.floor(Math.random() * presets.length)];
            container.appendChild(item);
            void item.offsetHeight;
            item.classList.add(preset);
            // 5-second skip lock — show a progress ring on the locked .state-line button.
            mountSkipLockRing();
            setTimeout(morphToContinue, 5000);
        }

        function renderBreakQuote(slotIndex) {
            const q = QUOTES[slotIndex] || { t: "", a: "", origin: "National", type: "fact" };
            const card = document.querySelector('#screen-break .break-card');
            const kicker = document.getElementById('break-kicker');
            const text = document.getElementById('break-text');
            // Facts keep "Bilarmidingiz?" above the text; quotes flip so the
            // author chip sits underneath as conventional attribution.
            const isQuote = q.type === 'quote';
            if (card) card.classList.toggle('break-card--quote', isQuote);
            if (kicker) {
                const defaultLabel = isQuote ? 'Iqtibos' : 'Bilarmidingiz?';
                kicker.textContent = q.a || defaultLabel;
            }
            if (text) {
                text.textContent = q.t || '';
                text.style.animation = 'none';
                void text.offsetHeight;
                text.style.animation = '';
            }
        }

        function mountSkipLockRing() {
            if (!btn || btn.querySelector('.skip-lock-ring')) return;
            const NS = 'http://www.w3.org/2000/svg';
            const svg = document.createElementNS(NS, 'svg');
            svg.setAttribute('class', 'skip-lock-ring');
            svg.setAttribute('viewBox', '0 0 22 22');
            const track = document.createElementNS(NS, 'circle');
            track.setAttribute('class', 'skip-track');
            track.setAttribute('cx', '11'); track.setAttribute('cy', '11'); track.setAttribute('r', '9');
            const progress = document.createElementNS(NS, 'circle');
            progress.setAttribute('class', 'skip-progress');
            progress.setAttribute('cx', '11'); progress.setAttribute('cy', '11'); progress.setAttribute('r', '9');
            svg.appendChild(track); svg.appendChild(progress);
            btn.appendChild(svg);
        }

        function morphToContinue() {
            const ring = btn && btn.querySelector('.skip-lock-ring');
            if (ring) ring.remove();
            btn.classList.remove('state-line');
            btn.classList.add('state-pill');
            if (btnText) {
                setBtnText(RT('btn.continue'));
            }
            btn.classList.add('pulse');
        }

        function startStage2() {
            state.isAnimating = true;
            btn.classList.remove('pulse');
            btn.classList.remove('state-pill');
            btn.classList.add('state-line');
            document.getElementById('screen-1').classList.remove('active');
            setTimeout(() => {
                document.getElementById('screen-2').classList.add('active');
                setStage(2);
                // Preview phase: 1 unit for the gate-quote continue plus 1
                // unit per *sub-page* of every panel. Counting sub-pages
                // (not just panel transitions) is what makes the bar move
                // while the student is actually reading a multi-page panel.
                // Back-swipes don't over-count because we track distinct
                // (panel,page) tokens in state.previewSeenPages.
                let totalPages = 0;
                if (typeof PANELS !== 'undefined' && Array.isArray(PANELS)) {
                    PANELS.forEach(p => {
                        const n = (p && Array.isArray(p.pages)) ? p.pages.length : 1;
                        totalPages += Math.max(1, n);
                    });
                }
                if (totalPages < 1) totalPages = 1;
                state.previewSeenPages = new Set();
                setPhaseRequired('preview', 1 + totalPages);
                // 1 unit for the gate-quote continue + 1 unit for the first
                // (panel 0, page 0) which is on screen the moment stage 2
                // mounts. Subsequent moves register through previewMarkPageSeen.
                state.previewSeenPages.add('0:0');
                setPhaseProgress('preview', 1 + state.previewSeenPages.size, 1 + totalPages);
                renderPanel();
                state.isAnimating = false;
            }, 500);
        }

        // Mark a (panel, page) pair as visited so the preview phase reflects
        // the student's actual reading progress through the panels. Distinct
        // pairs only — back-swiping doesn't double-count, and re-visiting an
        // earlier page doesn't push the bar past the highest unique count.
        function previewMarkPageSeen(panelIdx, pageIdx) {
            if (!state.previewSeenPages) state.previewSeenPages = new Set();
            const key = panelIdx + ':' + pageIdx;
            const before = state.previewSeenPages.size;
            state.previewSeenPages.add(key);
            if (state.previewSeenPages.size !== before) {
                // 1 (gate continue) + distinct pages seen so far.
                setPhaseProgress(
                    'preview',
                    1 + state.previewSeenPages.size,
                    completionState.preview.required
                );
            }
        }

        function renderPanel() {
            const panel = PANELS[state.panelIndex];
            const titleEl = document.getElementById('panel-title');
            if (titleEl) titleEl.innerText = panel.title;

            const container = document.getElementById('panel-content');
            const dots = document.getElementById('panel-dots');
            if (!container || !dots) return;

            container.innerHTML = '';
            dots.innerHTML = '';

            panel.pages.forEach((page, i) => {
                const pageEl = document.createElement('div');
                pageEl.className = `page ${i === state.pageIndex ? 'active' : ''}`;
                if (i < state.pageIndex) pageEl.style.transform = 'translateX(-100%)';
                if (i > state.pageIndex) pageEl.style.transform = 'translateX(100%)';

                page.blocks.forEach((block, bi) => {
                    let el;
                    if (block.type === 'h2') el = document.createElement('h2');
                    else if (block.type === 'p') el = document.createElement('p');
                    else if (block.type === 'ul' || block.type === 'ol') {
                        el = document.createElement(block.type);
                        block.items.forEach(txt => { const li = document.createElement('li'); li.innerHTML = txt; el.appendChild(li); });
                    }
                    else if (block.type === 'code') { el = document.createElement('code'); el.innerText = block.text; }
                    else if (block.type === 'quote') { el = document.createElement('blockquote'); el.innerText = block.text; }
                    else if (block.type === 'diagram') { el = document.createElement('div'); el.innerHTML = block.html; }
                    else if (block.type === 'image') {
                        el = document.createElement('div');
                        el.className = 'block-image';
                        const img = document.createElement('img');
                        img.src = block.src || '';
                        img.alt = block.alt || '';
                        img.loading = 'lazy';
                        el.appendChild(img);
                    }
                    else if (block.type === 'svg') {
                        el = document.createElement('div');
                        el.className = 'block-svg';
                        // block.html is raw SVG markup; insert as-is (authored content, not user input)
                        el.innerHTML = block.html || '';
                    }
                    else if (block.type === 'callout') {
                        // Builder schema doesn't formally support callout, but
                        // some imported homeworks carry it. Render as blockquote.
                        el = document.createElement('blockquote');
                        el.className = 'callout';
                        el.innerText = block.text || '';
                    }

                    // Defensive fallback: if the block type was unrecognized,
                    // render whatever text we have as a paragraph instead of
                    // crashing the whole panel.
                    if (!el) {
                        el = document.createElement('p');
                        el.className = 'block-unknown';
                        el.innerText = block.text || JSON.stringify(block).slice(0, 200);
                    }

                    if (block.text && !['code','quote','callout','diagram','image','svg'].includes(block.type)) el.innerHTML = block.text;
                    el.classList.add('bubbly');
                    pageEl.appendChild(el);

                    if (i === state.pageIndex) {
                        setTimeout(() => el.classList.add('show'), bi * 100 + 150);
                    } else {
                        el.classList.add('show');
                    }
                });
                container.appendChild(pageEl);

                const dot = document.createElement('div');
                dot.className = `dot ${i === state.pageIndex ? 'active' : ''}`;
                dot.onclick = () => { if (!state.isAnimating && i !== state.pageIndex) switchPage(i); };
                dots.appendChild(dot);
            });

            container.scrollTop = 0;
            updatePanelButton();
            updatePanelOverflowHint();
        }

        // Toggle the "more below" fade only when the active page actually
        // overflows its scroll container. Re-checks on resize / scroll / image
        // load so the hint stays accurate as content settles.
        function updatePanelOverflowHint() {
            const card = document.getElementById('panel-card');
            const container = document.getElementById('panel-content');
            if (!card || !container) return;
            const overflow = container.scrollHeight - container.clientHeight > 4
                && container.scrollTop + container.clientHeight < container.scrollHeight - 4;
            card.classList.toggle('has-overflow', overflow);
        }

        // Hook scroll + load events once. The handler is cheap (one DOM read).
        (function wirePanelOverflowHint() {
            const container = document.getElementById('panel-content');
            if (!container || container.dataset.overflowWired === '1') return;
            container.dataset.overflowWired = '1';
            container.addEventListener('scroll', updatePanelOverflowHint, { passive: true });
            window.addEventListener('resize', updatePanelOverflowHint);
            container.addEventListener('load', updatePanelOverflowHint, true);
        })();

        function updatePanelButton() {
            // NAV-01 + NAV-02 (2026-05-06): keep the CTA reachable on every preview
            // page so geometry homeworks like HW-20260505-005 (19 chunked pages
            // across 7 panels) don't trap the student behind a hidden state-line.
            // The chunker budget (PREVIEW_PAGE_BUDGET_PX) is intentionally NOT
            // touched so non-math subjects keep their existing page rhythm.
            const panel = PANELS[state.panelIndex];
            const isLastPage = state.pageIndex === panel.pages.length - 1;
            btn.classList.remove('state-pill', 'pulse', 'state-line');
            btn.classList.add('state-pill');
            if (isLastPage) {
                btn.classList.add('pulse');
                setBtnText(RT('btn.next_panel'));
            } else {
                // No pulse — pill is reachable but not visually "graduated yet".
                setBtnText(RT('btn.next_page'));
            }
        }

        function handleSwipe(dir) {
            if (state.isAnimating) return;
            if (state.stage === 3) {
                // Bug #6: also early-return on cardSwitching guard so rapid
                // horizontal swipes can't queue a second switch mid-transition.
                if (state.cardSwitching) return;
                // Clamp at boundaries — swiping past first/last card stays in
                // place instead of wrapping (UX: backward at card 1 must NOT
                // jump to the last card).
                if (dir === 'left' && state.cardIndex < FLASHCARDS.length - 1) {
                    switchCard(state.cardIndex + 1, 1);
                } else if (dir === 'right' && state.cardIndex > 0) {
                    switchCard(state.cardIndex - 1, -1);
                }
                return;
            }
            if (state.stage !== 2) return;
            const p = PANELS[state.panelIndex];
            if (dir === 'left') {
                if (state.pageIndex < p.pages.length - 1) switchPage(state.pageIndex + 1);
            } else if (dir === 'right') {
                if (state.pageIndex > 0) switchPage(state.pageIndex - 1);
                else if (state.panelIndex > 0) prevPanel();
            }
        }

        function showBreakScreen() {
            state.isAnimating = true;
            // Preview phase fully done — student finished all reading panels.
            completePhase('preview');
            renderBreakQuote(1);
            const content = document.getElementById('panel-content');
            if (content) {
                content.style.transition = 'all 400ms ease-in';
                content.style.transform = 'translateX(-100%)';
                content.style.filter = 'blur(15px)';
                content.style.opacity = '0';
            }
            btn.classList.remove('pulse');
            btn.classList.remove('state-pill');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            setTimeout(() => {
                document.getElementById('screen-2').classList.remove('active');
                document.getElementById('screen-break').classList.add('active');
                setStage(2.5);
                setTimeout(() => {
                    btn.classList.remove('state-line');
                    btn.classList.add('state-pill');
                    setBtnText(RT('btn.next'));
                    btn.classList.add('pulse');
                    state.isAnimating = false;
                }, 1500);
            }, 450);
        }

        function startStage3() {
            state.isAnimating = true;
            const breakScreen = document.getElementById('screen-break');
            if (breakScreen) breakScreen.style.opacity = '0';
            btn.classList.remove('pulse');
            btn.classList.remove('state-pill');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            setTimeout(() => {
                document.getElementById('screen-break').classList.remove('active');
                if (breakScreen) breakScreen.style.opacity = '';
                setStage(3);
                state.cardIndex = 0;
                state.cardFlipped = false;
                state.hintShown = false;
                // Honest progress: count distinct flashcard indices the
                // student has seen (not switchCard events). Wrap-around
                // browsing back to a card already in the set is a no-op.
                const fcCount = (typeof FLASHCARDS !== 'undefined' && Array.isArray(FLASHCARDS))
                    ? FLASHCARDS.length : 1;
                state.flashcardsSeen = new Set();
                state.flashcardsSeen.add(0);  // first card on screen
                setPhaseRequired('flashcards', fcCount);
                setPhaseProgress('flashcards', state.flashcardsSeen.size, fcCount);
                // Single-card phase: the only card on screen IS the last
                // card, so the Yakunlash CTA must be live from the first
                // paint — there's no swipe target to advance through.
                renderFlashcard(fcCount <= 1);
                document.getElementById('fc-inner').addEventListener('click', handleCardTap);
                setupFlashcardCarouselControls();
                document.getElementById('screen-3').classList.add('active');
                setTimeout(() => { state.isAnimating = false; }, 500);
            }, 450);
        }

        // Per-cluster colors. Drives both the chip and the aurora bloom
        // via the --fc-cluster CSS variable. Aurora tints derive from this
        // via color-mix() so we get matching low-opacity glows for free.
        const FC_CLUSTER_DOT = {
            'QOIDA':        '#0A84FF',  // rule    → blue
            'MISOL':        '#30D158',  // example → green
            'TAHLIL':       '#BF5AF2',  // analysis → purple
            'METOD':        '#FF9F0A',  // method  → orange
            // Legacy English names from older homeworks.
            'NAMES':        '#0A84FF',
            'FORMULAS':     '#BF5AF2',
            'DECISIONS':    '#30D158',
            'KEY INSIGHTS': '#FF9F0A',
        };
        // Legacy gradient palette — preserved as no-ops so old call sites
        // (side cards) stay valid until the side-card UI is also redesigned.
        const FC_CLUSTER_COLORS = {
            'QOIDA':        ['var(--fc-names-from)',    'var(--fc-names-to)'],
            'MISOL':        ['var(--fc-decisions-from)','var(--fc-decisions-to)'],
            'TAHLIL':       ['var(--fc-formulas-from)', 'var(--fc-formulas-to)'],
            'METOD':        ['var(--fc-insights-from)', 'var(--fc-insights-to)'],
            'NAMES':        ['var(--fc-names-from)',    'var(--fc-names-to)'],
            'FORMULAS':     ['var(--fc-formulas-from)', 'var(--fc-formulas-to)'],
            'DECISIONS':    ['var(--fc-decisions-from)','var(--fc-decisions-to)'],
            'KEY INSIGHTS': ['var(--fc-insights-from)', 'var(--fc-insights-to)'],
        };
        function fcApplyClusterDot(cluster, innerEl) {
            // Sets --fc-cluster on the .fc-inner wrapper. Both faces and
            // every aurora-derived token inherit, giving the whole card
            // a coherent cluster-color glow.
            const color = FC_CLUSTER_DOT[String(cluster || '').toUpperCase()] || '#0A84FF';
            innerEl.style.setProperty('--fc-cluster', color);
        }
        function fcApplySideGradient(cluster, sideEl) {
            const [from, to] = FC_CLUSTER_COLORS[cluster] || FC_CLUSTER_COLORS['QOIDA'];
            sideEl.style.setProperty('--fc-side-from', from);
            sideEl.style.setProperty('--fc-side-to', to);
        }
        function fcApplyMainMirror(card, mirrorEl) {
            if (!mirrorEl) return;
            const hasMedia = !!(card && card.front && card.front.media);
            mirrorEl.classList.toggle('has-media', hasMedia);
        }

        function fcFormatInlineMathHtml(value) {
            return String(value || '').replace(/([A-Za-z0-9αβγ])\^([0-9]+)/g, '$1<sup>$2</sup>');
        }

        function renderFlashcard(showYakunlash) {
            const card = FLASHCARDS[state.cardIndex];
            const total = FLASHCARDS.length;
            const n = state.cardIndex + 1;
            const clusterName = String(card.cluster || '').toLowerCase();

            // Top row: cluster name (lowercase, muted) — same on both faces.
            document.getElementById('fc-badge').textContent = clusterName;
            document.getElementById('fc-badge-back').textContent = clusterName;

            // Apply cluster dot color to the inner wrapper (cascades to both faces).
            const fcInner = document.getElementById('fc-inner');
            fcApplyClusterDot(card.cluster, fcInner);

            // Photo zone — shows ONLY structured card.front.media. Inline images
            // embedded in term_html stay inside the strip-term (sized small).
            const photoEl = document.getElementById('fc-photo');
            const mediaHtml = (card.front && card.front.media) ? String(card.front.media) : '';
            if (photoEl) photoEl.innerHTML = mediaHtml;

            // Term inside the frosted glass strip. innerHTML preserves any
            // inline <img>/<svg> the builder's RichField may have embedded.
            const termHtml = (card.front && (card.front.term_html || card.front.term)) || '';
            document.getElementById('fc-term').innerHTML = fcFormatInlineMathHtml(termHtml);

            // No-image variant: photo zone empty AND term has no inline media →
            // collapse photo zone, term scales up.
            const termHasInlineMedia = /<(img|svg)\b/i.test(termHtml);
            const hasAnyVisual = !!mediaHtml || termHasInlineMedia;
            fcInner.classList.toggle('no-image', !hasAnyVisual);

            const formulaEl = document.getElementById('fc-formula');
            if (card.front && card.front.formula) {
                formulaEl.textContent = card.front.formula;
                formulaEl.style.display = '';
            } else {
                formulaEl.style.display = 'none';
            }

            const defEl = document.getElementById('fc-definition');
            // innerHTML — back-of-card definition may contain inline images/SVGs/bold/italic.
            defEl.innerHTML = fcFormatInlineMathHtml((card.back && card.back.definition) || '');
            if (card.back && Array.isArray(card.back.bullets) && card.back.bullets.length) {
                const ul = document.createElement('ul');
                card.back.bullets.forEach(bullet => {
                    const li = document.createElement('li');
                    li.textContent = bullet;
                    ul.appendChild(li);
                });
                defEl.appendChild(ul);
            }

            // First-class Tip pill — shows the author's hint inline on the back.
            // No external below-the-card slot anymore.
            const tipEl = document.getElementById('fc-tip');
            const tipTextEl = document.getElementById('fc-tip-text');
            const hookText = (card.back && card.back.hook) ? String(card.back.hook).trim() : '';
            if (tipEl && tipTextEl) {
                if (hookText) {
                    // innerHTML — author hints may contain inline <strong>/<i>/<br>
                    // for emphasis (same trust model as back.definition above).
                    tipTextEl.innerHTML = hookText;
                    tipEl.classList.remove('is-empty');
                } else {
                    tipTextEl.textContent = '';
                    tipEl.classList.add('is-empty');
                }
            }

            const counterText = n + ' / ' + total;
            document.getElementById('fc-counter-front').textContent = counterText;
            document.getElementById('fc-counter-back').textContent = counterText;
            renderFlashcardSides();

            // Bug #6 defensive reset: rapid horizontal switches can leave
            // inline transform/opacity on fcInner if a previous transition
            // was interrupted. Clearing them here guarantees the freshly
            // rendered card paints at its rest position even when the
            // carousel guard didn't get a clean release.
            fcInner.style.transition = 'none';
            fcInner.style.transform = '';
            fcInner.style.opacity = '';
            fcInner.style.filter = '';
            fcInner.classList.remove('flipped');
            fcInner.classList.remove('fc-sliding-flipped');
            state.cardFlipped = false;

            const hintEl = document.getElementById('fc-hint');
            if (!state.hintShown) {
                hintEl.style.opacity = '1';
            } else {
                hintEl.style.opacity = '0';
            }

            if (showYakunlash) {
                btn.classList.remove('state-line');
                btn.classList.add('state-pill');
                setBtnText(RT('btn.finish'));
                btn.classList.add('pulse');
            }

        }

        function getWrappedCardIndex(idx) {
            const total = FLASHCARDS.length;
            return (idx + total) % total;
        }

        function fcStripHtml(value) {
            const el = document.createElement('div');
            el.innerHTML = String(value || '');
            return (el.textContent || '').trim();
        }

        function setSideCardContent(prefix, card, index, total) {
            document.getElementById(prefix + '-term').textContent =
                (card.front && (card.front.term || fcStripHtml(card.front.term_html || ''))) || '';
            const formulaEl = document.getElementById(prefix + '-formula');
            if (card.front && card.front.formula) {
                formulaEl.textContent = card.front.formula;
                formulaEl.style.display = '';
            } else {
                formulaEl.style.display = 'none';
            }
            document.getElementById(prefix + '-counter').textContent = (index + 1) + ' / ' + total;
        }

        function renderFlashcardSides() {
            const total = FLASHCARDS.length;
            const currentCard = FLASHCARDS[state.cardIndex];
            // Boundary-aware: at the first card there is no previous; at the
            // last card there is no next. We hide those side rails (and their
            // mirror twins) instead of wrapping, so clicking them can't jump
            // the carousel to the opposite end.
            const atFirst = state.cardIndex <= 0;
            const atLast = state.cardIndex >= total - 1;
            const prevIndex = atFirst ? state.cardIndex : state.cardIndex - 1;
            const nextIndex = atLast ? state.cardIndex : state.cardIndex + 1;
            setSideCardContent('fc-prev', FLASHCARDS[prevIndex], prevIndex, total);
            setSideCardContent('fc-next', FLASHCARDS[nextIndex], nextIndex, total);
            const prevEl = document.getElementById('fc-prev-card');
            const nextEl = document.getElementById('fc-next-card');
            const prevMirror = document.getElementById('fc-mirror-prev');
            const mainMirror = document.getElementById('fc-mirror-main');
            const nextMirror = document.getElementById('fc-mirror-next');
            if (prevEl) {
                fcApplySideGradient(FLASHCARDS[prevIndex].cluster, prevEl);
                prevEl.style.visibility = atFirst ? 'hidden' : '';
                prevEl.setAttribute('aria-hidden', atFirst ? 'true' : 'false');
            }
            if (nextEl) {
                fcApplySideGradient(FLASHCARDS[nextIndex].cluster, nextEl);
                nextEl.style.visibility = atLast ? 'hidden' : '';
                nextEl.setAttribute('aria-hidden', atLast ? 'true' : 'false');
            }
            if (prevMirror) {
                fcApplySideGradient(FLASHCARDS[prevIndex].cluster, prevMirror);
                prevMirror.style.visibility = atFirst ? 'hidden' : '';
            }
            fcApplyMainMirror(currentCard, mainMirror);
            if (nextMirror) {
                fcApplySideGradient(FLASHCARDS[nextIndex].cluster, nextMirror);
                nextMirror.style.visibility = atLast ? 'hidden' : '';
            }
        }

        function setupFlashcardCarouselControls() {
            const prevEl = document.getElementById('fc-prev-card');
            const nextEl = document.getElementById('fc-next-card');
            // Bug #6 guard: state.cardSwitching is the in-flight horizontal
            // transition guard set inside switchCard. While it's true every
            // entry point (side-card click, keyboard arrow, swipe) early-
            // returns so a second switch can't hide the center face mid-fade.
            const rotateToPrev = () => {
                if (state.stage !== 3 || state.isAnimating || state.cardSwitching) return;
                // Stay at first card — clicking the prev side card on card 1
                // must NOT wrap to the last card.
                if (state.cardIndex <= 0) return;
                switchCard(state.cardIndex - 1, -1);
            };
            const rotateToNext = () => {
                if (state.stage !== 3 || state.isAnimating || state.cardSwitching) return;
                if (state.cardIndex >= FLASHCARDS.length - 1) return;
                switchCard(state.cardIndex + 1, 1);
            };
            if (prevEl) {
                prevEl.onclick = rotateToPrev;
                prevEl.onkeydown = (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        rotateToPrev();
                    }
                };
            }
            if (nextEl) {
                nextEl.onclick = rotateToNext;
                nextEl.onkeydown = (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        rotateToNext();
                    }
                };
            }
        }
        function handleCardTap(e) {
            if (state.stage !== 3) return;
            if (state.isAnimating) return;
            state.isAnimating = true;

            if (!state.hintShown) {
                state.hintShown = true;
                const hintEl = document.getElementById('fc-hint');
                hintEl.style.opacity = '0';
            }

            const fcInner = document.getElementById('fc-inner');
            // Tap-pop micro-interaction — a 280ms shadow swell on the leading face.
            // We force-restart the animation so consecutive taps each pop.
            fcInner.classList.remove('tap-pop');
            void fcInner.offsetWidth;
            fcInner.classList.add('tap-pop');

            fcInner.style.transition = 'transform 500ms cubic-bezier(0.4, 0.0, 0.2, 1)';
            state.cardFlipped = !state.cardFlipped;
            fcInner.classList.toggle('flipped', state.cardFlipped);

            setTimeout(() => { state.isAnimating = false; }, 520);
        }

        function switchCard(newIdx, dir) {
            // Bug #6: rapid right-arrow / right-side-card clicks during the
            // transition could leave the center face hidden because a second
            // switch fired before the first cleared its inline opacity:0.
            // The state.cardSwitching guard short-circuits any re-entry while
            // a horizontal switch is in flight; setupFlashcardCarouselControls,
            // handleSwipe, and dot handlers all early-return when it's true.
            if (state.cardSwitching) return;
            state.cardSwitching = true;
            state.isAnimating = true;
            const scene = document.querySelector('.fc-scene');
            if (scene) {
                scene.classList.remove('is-rotating-left', 'is-rotating-right');
                void scene.offsetWidth;
                scene.classList.add(dir > 0 ? 'is-rotating-left' : 'is-rotating-right');
            }
            const fcInner = document.getElementById('fc-inner');
            fcInner.removeEventListener('click', handleCardTap);

            // Flipped card during a horizontal switch: swap to a flat-back
            // render BEFORE animating, so the slide is a pure 2D translate.
            // Preserving the parent rotateY(180deg) through the transition
            // is unreliable — browser matrix interpolation at 180° can
            // pick a path that mid-rotates the card and triggers backface-
            // visibility hiding mid-slide. The .fc-sliding-flipped class
            // un-rotates the back face and fades the front so the back
            // content stays visible flat throughout the slide. Transition
            // is disabled for the swap so the un-flip is instant, then
            // re-enabled for the slide.
            if (state.cardFlipped) {
                fcInner.style.transition = 'none';
                fcInner.classList.remove('flipped');
                fcInner.classList.add('fc-sliding-flipped');
                void fcInner.offsetWidth;
            }
            fcInner.style.transition = 'transform 350ms ease-in-out, opacity 350ms ease-in-out, filter 350ms ease-in-out';
            fcInner.style.transform = `translateX(${dir * -80}px)`;
            fcInner.style.filter = 'blur(10px)';
            fcInner.style.opacity = '0';

            // Two paths to release the guard so it never hangs: (1) a real
            // transitionend event on fcInner, (2) a 420ms safety timeout
            // covering the case where transitionend doesn't fire (background
            // tab, transition cancelled by another inline-style write, etc.).
            // releaseGuard() is idempotent — both paths can fire safely.
            let guardReleased = false;
            const releaseGuard = () => {
                if (guardReleased) return;
                guardReleased = true;
                fcInner.style.transition = '';
                fcInner.style.transform = '';
                fcInner.style.filter = '';
                fcInner.style.opacity = '';
                // Re-assert flipped face cleared (defensive for the case
                // where renderFlashcard's reset was skipped or interrupted).
                fcInner.classList.remove('flipped');
                fcInner.classList.remove('fc-sliding-flipped');
                state.cardFlipped = false;
                fcInner.addEventListener('click', handleCardTap, { once: false });
                if (scene) scene.classList.remove('is-rotating-left', 'is-rotating-right');
                state.isAnimating = false;
                state.cardSwitching = false;
            };

            setTimeout(() => {
                state.cardIndex = newIdx;
                // Honest progress: only distinct card indices count. Going
                // back to a card already in the set is a no-op; wrap-around
                // can't push past required.
                if (!state.flashcardsSeen) state.flashcardsSeen = new Set();
                const beforeSize = state.flashcardsSeen.size;
                state.flashcardsSeen.add(newIdx);
                if (state.flashcardsSeen.size !== beforeSize) {
                    setPhaseProgress(
                        'flashcards',
                        state.flashcardsSeen.size,
                        completionState.flashcards.required
                    );
                }
                const showYakunlash = (newIdx === FLASHCARDS.length - 1);
                renderFlashcard(showYakunlash);

                fcInner.style.transition = 'none';
                fcInner.style.transform = `translateX(${dir * 80}px)`;
                fcInner.style.filter = 'blur(10px)';
                fcInner.style.opacity = '0';
                void fcInner.offsetHeight;

                requestAnimationFrame(() => {
                    fcInner.style.transition = 'transform 350ms ease-in-out, opacity 350ms ease-in-out, filter 350ms ease-in-out';
                    fcInner.style.transform = 'translateX(0)';
                    fcInner.style.filter = 'blur(0)';
                    fcInner.style.opacity = '1';
                });

                // Listen for the in-transition transitionend; first opacity
                // event after the slide-in is enough. Then a 420ms fallback
                // (slightly longer than the 380ms transform duration) covers
                // the case where transitionend never fires.
                const onEnd = (e) => {
                    if (e && e.target !== fcInner) return;
                    fcInner.removeEventListener('transitionend', onEnd);
                    releaseGuard();
                };
                fcInner.addEventListener('transitionend', onEnd);
                setTimeout(() => {
                    fcInner.removeEventListener('transitionend', onEnd);
                    releaseGuard();
                }, 420);
            }, 360);
        }

        function endStage3() {
            if (state.isAnimating) return;
            state.isAnimating = true;
            // Flashcards phase done — student finished or chose Yakunlash.
            completePhase('flashcards');
            renderBreakQuote(2);
            const fcInner = document.getElementById('fc-inner');
            if (fcInner) {
                fcInner.removeEventListener('click', handleCardTap);
                fcInner.style.transition = 'opacity 400ms ease';
                fcInner.style.opacity = '0';
            }
            btn.classList.remove('pulse');
            btn.classList.remove('state-pill');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            setTimeout(() => {
                document.getElementById('screen-3').classList.remove('active');
                document.getElementById('screen-break').classList.add('active');
                setStage(3.5);
                setTimeout(() => {
                    btn.classList.remove('state-line');
                    btn.classList.add('state-pill');
                    setBtnText(RT('btn.next'));
                    btn.classList.add('pulse');
                    state.isAnimating = false;
                }, 1500);
            }, 450);
        }

        const MS_QUESTIONS = [
            {
                type: "KO",
                prompt: "Quyidagi tenglamalardan qaysi biri kvadrat tenglama?",
                subtitle: "Which of the following is a quadratic equation?",
                tags: "[Bloom: L1 | PISA: L1]",
                explain: "Ko'nikma: aniqlash, xotira",
                options: ["3x + 5 = 0", "x\u00b2 \u2013 7 = 0", "x\u00b3 \u2013 x = 0", "2x + 3y = 0"],
                correct: 1
            },
            {
                type: "KO",
                prompt: "5x\u00b2 \u2013 3x + 7 = 0 tenglamaning bosh koeffitsiyenti qaysi?",
                subtitle: "What is the leading coefficient in 5x\u00b2 \u2013 3x + 7 = 0?",
                tags: "[Bloom: L1 | PISA: L1]",
                explain: "Ko'nikma: terminologiya, xotira",
                options: ["5", "\u20133", "7", "\u20135"],
                correct: 0
            },
            {
                type: "To\u02bcg\u02bcri / Noto\u02bcg\u02bcri",
                prompt: "0\u00b7x\u00b2 + 5x \u2013 2 = 0 kvadrat tenglama hisoblanadi.",
                subtitle: "The equation 0\u00b7x\u00b2 + 5x \u2013 2 = 0 is a quadratic equation.",
                tags: "[Bloom: L2 | PISA: L2]",
                explain: "Agar a = 0 bo\u02bcsa, x\u00b2 yo\u02bcqoladi va tenglama chiziqli bo\u02bclib qoladi.",
                options: ["To\u02bcg\u02bcri", "Noto\u02bcg\u02bcri", "Faqat ba\u02bczan", "Aniq emas"],
                correct: 1
            },
            {
                type: "KO",
                prompt: "x\u00b2 = 25 tenglamaning nechta haqiqiy ildizi bor?",
                subtitle: "How many real roots does the equation x\u00b2 = 25 have?",
                tags: "[Bloom: L2 | PISA: L1]",
                explain: "Ko'nikma: xotira, qo'llash",
                options: ["0", "1", "2", "Cheksiz ko\u02bcop"],
                correct: 2
            },
            {
                type: "Ha / Yo\u02bcq / Aniq emas",
                prompt: "\"Har qanday kvadrat tenglama aniq ikkita haqiqiy ildizga ega\" fikri to\u02bcg\u02bcrimi?",
                subtitle: "Evaluate the statement: Every quadratic equation has exactly two real roots.",
                tags: "[Bloom: L2 | PISA: L2]",
                explain: "Kvadrat tenglama 0, 1 yoki 2 ta haqiqiy ildizga ega bo\u02bclib qoladi.",
                options: ["Ha", "Yo\u02bcq", "Aniq emas", "Faqat x\u00b2=d da"],
                correct: 1
            },
            {
                type: "KO",
                prompt: "\u20137x\u00b2 \u2013 13x + 8 = 0 tenglamaning ozod hadi qaysi?",
                subtitle: "What is the free term in \u20137x\u00b2 \u2013 13x + 8 = 0?",
                tags: "[Bloom: L1 | PISA: L1]",
                explain: "Ko'nikma: terminologiya, xotira",
                options: ["\u20137", "\u201313", "8", "x\u00b2"],
                correct: 2
            }
        ];

        const msState = {
            index: 0,
            score: 0,
            isAnimating: false,
            revealTimer: null,
            advanceTimer: null,
            skipHandler: null
        };

        function msClearAdvanceTimers() {
            if (msState.revealTimer) { clearTimeout(msState.revealTimer); msState.revealTimer = null; }
            if (msState.advanceTimer) { clearTimeout(msState.advanceTimer); msState.advanceTimer = null; }
            if (msState.skipHandler) {
                document.removeEventListener('pointerdown', msState.skipHandler, true);
                document.removeEventListener('click', msState.skipHandler, true);
                document.removeEventListener('touchstart', msState.skipHandler, true);
                document.removeEventListener('keydown', msState.skipHandler, true);
                msState.skipHandler = null;
            }
        }

        // Estimate the time a student needs to actually READ the
        // explanation card before auto-advancing. 220 wpm is the
        // mid-range adult silent-reading speed; commas / sentence
        // terminators add the small natural pauses a reader takes;
        // +3 s is a base "saw it land + recognised the verdict"
        // buffer. Returns milliseconds. The text may arrive as HTML
        // (explainer uses innerHTML for inline images / SVG / bold),
        // so strip tags before counting words.
        function msReadingDelayMs(rawHtml) {
            const text = String(rawHtml || '').replace(/<[^>]*>/g, ' ').trim();
            if (!text) return 900;
            const words = text.split(/\s+/).filter(Boolean);
            const wordCount = words.length;
            const commas = (text.match(/,/g) || []).length;
            const periods = (text.match(/[.!?]/g) || []).length;
            const seconds =
                (wordCount / 220) * 60 +
                commas * 0.15 +
                periods * 0.3 +
                3;
            // Clamp so a one-word explanation still gets the base buffer
            // and an unreasonably long one can't soft-lock the UI without
            // user input — click-to-skip is always available either way.
            const ms = Math.round(seconds * 1000);
            return Math.max(3000, Math.min(ms, 15000));
        }

        // Layout positions for N visible option buttons inside the
        // 88vw / 640px answer zone. Counts < 4 used to share the static
        // 4-quad layout, leaving "undefined" buttons in the empty slots
        // for True/False (2 options) and Yes/No/Not Given (3 options).
        // For >4 options the static layout silently truncated. This
        // function returns an N-length array of {left, top} pairs that
        // packs the buttons into 1 or 2 rows depending on count.
        function msPositionsFor(n) {
            if (n <= 1) return [{ left: '50%', top: '50%' }];
            if (n === 2) return [
                { left: '25%', top: '50%' },
                { left: '75%', top: '50%' }
            ];
            if (n === 3) return [
                { left: '50%', top: '28%' },
                { left: '25%', top: '74%' },
                { left: '75%', top: '74%' }
            ];
            if (n === 4) return [
                { left: '25%', top: '28%' },
                { left: '75%', top: '28%' },
                { left: '25%', top: '74%' },
                { left: '75%', top: '74%' }
            ];
            const top = Math.ceil(n / 2);
            const bot = n - top;
            const out = [];
            for (let i = 0; i < top; i++) {
                out.push({ left: ((i + 0.5) * 100 / top).toFixed(2) + '%', top: '28%' });
            }
            for (let i = 0; i < bot; i++) {
                out.push({ left: ((i + 0.5) * 100 / bot).toFixed(2) + '%', top: '74%' });
            }
            return out;
        }

        // Append additional `.ms-option-btn` elements to the answer zone
        // until at least `count` buttons exist. Used when a question
        // supplies more than the 4 static buttons. Click handlers are
        // bound here because the global init() loop only saw the static
        // four at page load.
        function msEnsureOptionButtons(zone, count) {
            if (!zone) return;
            const existing = zone.querySelectorAll('.ms-option-btn');
            for (let i = existing.length; i < count; i++) {
                const b = document.createElement('button');
                b.className = 'ms-option-btn tappable';
                b.id = 'ms-opt-' + i;
                b.type = 'button';
                b.setAttribute('aria-label', 'Variant ' + (i + 1));
                b.addEventListener('click', () => msHandleAnswer(i));
                zone.appendChild(b);
            }
        }

        function startMemorySprintPhase() {
            setStage(4);
            msState.index = 0;
            msState.score = 0;
            msState.isAnimating = true;
            // Real completion: 1 unit per sprint question answered.
            const msTotal = (typeof MS_QUESTIONS !== 'undefined' && Array.isArray(MS_QUESTIONS))
                ? MS_QUESTIONS.length : 1;
            setPhaseRequired('sprint', msTotal);

            const screenMs = document.getElementById('screen-ms');
            if (screenMs) screenMs.classList.add('active');

            const centerCard = document.getElementById('ms-phase-center-card');
            const anchor = document.getElementById('ms-phase-anchor');
            const quizShell = document.getElementById('ms-quiz-shell');
            const qBox = document.getElementById('ms-question-box');
            const resultPanel = document.getElementById('ms-result-panel');

            if (resultPanel) resultPanel.style.display = 'none';
            if (quizShell) quizShell.classList.remove('visible');
            if (centerCard) { centerCard.style.display = ''; centerCard.style.animation = ''; }
            if (anchor) { anchor.classList.remove('show'); anchor.style.display = 'none'; }

            const optBtns = document.querySelectorAll('.ms-option-btn');
            optBtns.forEach(b => {
                b.classList.remove('correct', 'wrong', 'merging', 'visible');
                b.disabled = false;
            });

            btn.classList.remove('pulse', 'state-pill');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';

            setTimeout(() => {
                if (centerCard) centerCard.style.animation = 'fadeOutDown 700ms ease forwards';
            }, 1200);

            setTimeout(() => {
                if (centerCard) centerCard.style.display = 'none';
                if (quizShell) quizShell.classList.add('visible');
                if (qBox) qBox.classList.add('visible');
                msRenderQuestion(msState.index, true);
                msState.isAnimating = false;
                state.isAnimating = false;
            }, 1950);
        }

        function msRenderQuestion(index, immediate) {
            const item = MS_QUESTIONS[index];
            const stepEl = document.getElementById('ms-question-step');
            const tagsEl = document.getElementById('ms-question-tags');
            const titleEl = document.getElementById('ms-question-title');
            const subtitleEl = document.getElementById('ms-question-subtitle');
            const explainerEl = document.getElementById('ms-question-explainer');
            if (stepEl) stepEl.textContent = RT('ms.question_prefix') + ' ' + (index + 1) + ' / ' + MS_QUESTIONS.length + ' \u00b7 ' + item.type;
            if (tagsEl) tagsEl.textContent = item.tags;
            // innerHTML \u2014 prompt/explain may contain inline images/SVGs/bold/italic.
            if (titleEl) titleEl.innerHTML = item.prompt || '';
            if (subtitleEl) subtitleEl.textContent = item.subtitle;
            // Explanation MUST start hidden on every render — no leakage
            // from the previous question's revealed state.
            msClearAdvanceTimers();
            if (explainerEl) {
                explainerEl.classList.remove('is-shown');
                explainerEl.innerHTML = item.explain || '';
            }

            const opts = Array.isArray(item.options) ? item.options : [];
            const zone = document.getElementById('ms-answer-zone');
            // Grow the button pool first (needed for MC questions with
            // 5+ options that previously got silently truncated).
            msEnsureOptionButtons(zone, opts.length);
            const positions = msPositionsFor(opts.length);
            const optBtns = document.querySelectorAll('.ms-option-btn');
            optBtns.forEach((b, i) => {
                b.classList.remove('correct', 'wrong', 'merging', 'visible');
                if (i < opts.length) {
                    b.disabled = false;
                    b.classList.remove('is-hidden');
                    b.textContent = opts[i];
                    // Keep accessible name synced with visible text — the
                    // static aria-label="Variant N" is a pre-JS fallback;
                    // once we have real option text, that is more useful.
                    b.setAttribute('aria-label', opts[i] || ('Variant ' + (i + 1)));
                    b.style.left = '50%';
                    b.style.top = '50%';
                    b.style.transform = 'translate(-50%, -50%) scale(0.15)';
                } else {
                    // Hide unused buttons completely so True/False (2) and
                    // YNNG (3) questions don't render literal "undefined"
                    // tappable buttons in the empty slots.
                    b.classList.add('is-hidden');
                    b.disabled = true;
                    b.textContent = '';
                    b.removeAttribute('aria-label');
                }
            });

            const reveal = () => {
                optBtns.forEach((b, i) => {
                    if (i >= opts.length) return;
                    const pos = positions[i] || { left: '50%', top: '50%' };
                    b.style.left = pos.left;
                    b.style.top = pos.top;
                    b.style.transform = 'translate(-50%, -50%) scale(1)';
                    b.classList.add('visible');
                });
            };

            if (immediate) {
                requestAnimationFrame(reveal);
            } else {
                setTimeout(reveal, 120);
            }
        }

        function msHandleAnswer(selectedIndex) {
            if (msState.isAnimating) return;
            if (state.stage !== 4) return;
            msState.isAnimating = true;

            const item = MS_QUESTIONS[msState.index];
            const localCorrect = selectedIndex === item.correct;
            if (localCorrect) msState.score++;
            // Log Memory Sprint result for end-of-session AMR scorecard.
            // Closed multiple-choice — score-only, no AI axes.
            if (window.__sessionLog) {
                window.__sessionLog.push({
                    phase: 'memory-sprint', id: 'ms-' + (msState.index + 1),
                    correct: localCorrect, score: localCorrect ? 1 : 0,
                });
            }

            const optsLen = Array.isArray(item.options) ? item.options.length : 0;
            const optBtns = document.querySelectorAll('.ms-option-btn');
            optBtns.forEach((b, i) => {
                b.disabled = true;
                if (i >= optsLen) return; // skip hidden TF/YNNG slots
                if (i === item.correct) b.classList.add('correct');
                else b.classList.add('wrong');
            });

            // Fire-and-forget telemetry / backend consistency check.
            // Local match already drove the UI above; backend result is for
            // logging/consistency only.  We do NOT block the animation on it.
            (function() {
                const questionId = 'ms-' + msState.index;
                const ctx = window.NETS_CTX || {};
                const answerSpec = item.answer_spec || {
                    type: 'option_index',
                    expected: item.correct,
                    option_count: (item.options || []).length,
                    allow_ai_fallback: false
                };
                document.dispatchEvent(new CustomEvent('nets:submit', {
                    detail: {
                        kind: 'memory-sprint',
                        payload: {
                            questionId: questionId,
                            studentAnswer: String(selectedIndex),
                            answerSpec: answerSpec,
                            subject: ctx.subject || 'math-algebra',
                            grade: ctx.grade || 8,
                            phase: 'memory_sprint'
                        }
                    }
                }));
                // Listen once for the result to detect fixture drift.
                function onResult(ev) {
                    const d = ev.detail || {};
                    if (d.kind !== 'memory-sprint') return;
                    document.removeEventListener('nets:result', onResult);
                    const result = d.result || {};
                    if (result.source === 'deterministic') {
                        const backendCorrect = result.correct === true;
                        if (backendCorrect !== localCorrect) {
                            console.warn(
                                '[NETS] memory_sprint consistency mismatch at index',
                                msState.index,
                                '— local:', localCorrect,
                                'backend:', backendCorrect,
                                '. Check answer_spec in fixture.'
                            );
                        }
                    }
                }
                document.addEventListener('nets:result', onResult);
            })();

            // Options are locked + correctness shown above. Reveal the
            // explanation card after a short beat, then auto-advance —
            // unless the user taps anywhere to skip the wait early.
            const explainerEl = document.getElementById('ms-question-explainer');
            const hasExplain = !!(explainerEl && (item.explain || '').trim());

            const advanceNow = () => {
                msClearAdvanceTimers();
                msCollapseToLoader();
            };

            if (hasExplain) {
                msState.revealTimer = setTimeout(() => {
                    msState.revealTimer = null;
                    explainerEl.classList.add('is-shown');
                    // Bind skip-to-next AFTER reveal so the user input that
                    // triggered this flow can't immediately fire the skip.
                    // Use pointerdown so any tap/click anywhere skips on the
                    // very first input (capture phase, before bubbling).
                    msState.skipHandler = (ev) => { advanceNow(); };
                    document.addEventListener('pointerdown', msState.skipHandler, true);
                    document.addEventListener('click', msState.skipHandler, true);
                    document.addEventListener('touchstart', msState.skipHandler, true);
                    document.addEventListener('keydown', msState.skipHandler, true);
                    // Auto-advance delay scales with how long the
                    // explanation actually takes to read — short hints
                    // get the 3 s base buffer, paragraph-length recaps
                    // get the time their words + punctuation deserve.
                    // Click-to-skip is still bound above, so the cap
                    // here only matters when the student doesn't tap.
                    msState.advanceTimer = setTimeout(
                        advanceNow,
                        msReadingDelayMs(item.explain)
                    );
                }, 320);
            } else {
                msState.advanceTimer = setTimeout(advanceNow, 900);
            }
        }

        function msCollapseToLoader() {
            msClearAdvanceTimers();
            const explainerEl = document.getElementById('ms-question-explainer');
            if (explainerEl) explainerEl.classList.remove('is-shown');
            const optBtns = document.querySelectorAll('.ms-option-btn');
            optBtns.forEach(b => {
                if (b.classList.contains('is-hidden')) return;
                b.classList.add('merging');
                b.style.left = '50%';
                b.style.top = '50%';
                b.style.transform = 'translate(-50%, -50%) scale(1)';
            });

            const qBox = document.getElementById('ms-question-box');
            if (qBox) { qBox.classList.remove('visible'); qBox.classList.add('out'); }

            setTimeout(() => {
                if (qBox) qBox.classList.remove('out');
                msState.index++;
                // Real student action: just answered a sprint question.
                bumpPhase('sprint', 1);
                if (msState.index >= MS_QUESTIONS.length) {
                    msFinishSprint();
                    return;
                }
                msRenderQuestion(msState.index, false);
                if (qBox) qBox.classList.add('visible');
                msState.isAnimating = false;
            }, 1050);
        }

        function msFinishSprint() {
            // Sprint phase done — student answered (or skipped to) the end.
            completePhase('sprint');
            const quizShell = document.getElementById('ms-quiz-shell');
            const resultPanel = document.getElementById('ms-result-panel');
            if (quizShell) quizShell.classList.remove('visible');
            if (resultPanel) resultPanel.style.display = 'flex';

            const scoreEl = document.getElementById('ms-result-score');
            const copyEl = document.getElementById('ms-result-copy');
            if (scoreEl) scoreEl.textContent = msState.score + ' / ' + MS_QUESTIONS.length;
            if (copyEl) copyEl.textContent = msState.score >= 5
                ? RT('ms.score_great')
                : RT('ms.score_meh');

            btn.classList.remove('state-line');
            btn.classList.add('state-pill', 'pulse');
            // Pick label based on which phase actually comes next: Reading (Til
            // pipeline) sits between MS and Game Breaks and auto-skips when empty.
            // Hardcoding "Game break" before Reading misleads the student.
            const nextIsReading = (typeof readingHasContent === 'function') && readingHasContent();
            setBtnText(RT(nextIsReading ? 'btn.read' : 'btn.game_break'));
            setStage(4.5);
            msState.isAnimating = false;
        }

        // ── Bug #5/#7 — shared sliding-panel helper (wave2 streams) ──────
        // Mirrors Preview's switchPage animation recipe (transform +
        // filter + opacity, 50ms wait + reflow + requestAnimationFrame +
        // 500ms cleanup) byte-for-byte, but operates on independent
        // streams keyed by container id so Reading and Consolidation can
        // each have their own without colliding with Preview.
        //
        // Consumers are responsible for putting .wave2-slide-page child
        // elements into the container before calling wave2SlideInit.
        // The helper handles: opacity/transform stage management, dot
        // indicator rendering, navigation animations, exit hooks.
        const _wave2Streams = {};

        function wave2SlideInit(opts) {
            const container = document.getElementById(opts.containerId);
            if (!container) return null;
            const pages = container.querySelectorAll(':scope > .wave2-slide-page');
            pages.forEach((p, i) => {
                p.classList.toggle('wave2-active', i === 0);
                if (i !== 0) {
                    p.style.transform = 'translateX(100%)';
                    p.style.opacity = '0';
                }
            });
            const dotsRow = opts.dotsId ? document.getElementById(opts.dotsId) : null;
            if (dotsRow) {
                dotsRow.innerHTML = '';
                for (let i = 0; i < opts.panelCount; i++) {
                    const dot = document.createElement('div');
                    dot.className = 'wave2-dot' + (i === 0 ? ' wave2-active' : '');
                    dotsRow.appendChild(dot);
                }
            }
            const stream = {
                containerId: opts.containerId,
                dotsId: opts.dotsId,
                index: 0,
                panelCount: opts.panelCount,
                canAdvance: opts.canAdvance || (() => true),
                onSettle: opts.onSettle || (() => {}),
                onExitForward: opts.onExitForward || (() => {}),
                onExitBackward: opts.onExitBackward || (() => {}),
                isAnimating: false,
            };
            _wave2Streams[opts.containerId] = stream;
            return stream;
        }

        function wave2SlideNavigate(containerId, dir) {
            const stream = _wave2Streams[containerId];
            if (!stream || stream.isAnimating) return;
            const newIdx = stream.index + dir;
            if (newIdx < 0) { stream.onExitBackward(); return; }
            if (newIdx >= stream.panelCount) { stream.onExitForward(); return; }
            if (!stream.canAdvance(stream.index, newIdx)) return;
            wave2SlideTo(containerId, newIdx);
        }

        function wave2SlideTo(containerId, idx) {
            const stream = _wave2Streams[containerId];
            if (!stream || stream.isAnimating) return;
            if (idx < 0 || idx >= stream.panelCount || idx === stream.index) return;
            const container = document.getElementById(containerId);
            if (!container) return;
            const pages = container.querySelectorAll(':scope > .wave2-slide-page');
            const cur = pages[stream.index];
            const nxt = pages[idx];
            if (!cur || !nxt) return;

            stream.isAnimating = true;
            const dir = idx > stream.index ? 1 : -1;

            // Animate current OUT (mirrors Preview's switchPage exactly).
            cur.style.transform = `translateX(${dir * -100}%)`;
            cur.style.filter = 'blur(15px)';
            cur.style.opacity = '0';

            setTimeout(() => {
                cur.classList.remove('wave2-active');
                nxt.style.transition = 'none';
                nxt.style.transform = `translateX(${dir * 100}%)`;
                nxt.style.filter = 'blur(15px)';
                nxt.style.opacity = '0';
                void nxt.offsetHeight;

                requestAnimationFrame(() => {
                    nxt.style.transition = 'all 450ms cubic-bezier(0.2, 0.8, 0.2, 1)';
                    nxt.style.transform = 'translateX(0)';
                    nxt.style.filter = 'blur(0)';
                    nxt.style.opacity = '1';
                    nxt.classList.add('wave2-active');
                });

                stream.index = idx;
                if (stream.dotsId) {
                    const dotsRow = document.getElementById(stream.dotsId);
                    if (dotsRow) {
                        const dots = dotsRow.querySelectorAll('.wave2-dot');
                        dots.forEach((d, i) => d.classList.toggle('wave2-active', i === idx));
                    }
                }
                try { stream.onSettle(idx); } catch (e) { /* swallow */ }

                setTimeout(() => {
                    [cur, nxt].forEach(el => {
                        el.style.transition = '';
                        el.style.transform = '';
                        el.style.filter = '';
                        el.style.opacity = '';
                    });
                    stream.isAnimating = false;
                }, 500);
            }, 50);
        }

        function wave2SlideDestroy(containerId) {
            delete _wave2Streams[containerId];
        }

        function switchPage(idx) {
            state.isAnimating = true;
            const pages = document.querySelectorAll('.page');
            const curIdx = state.pageIndex;
            const dir = idx > curIdx ? 1 : -1;
            const container = document.getElementById('panel-content');

            pages[curIdx].style.transform = `translateX(${dir * -100}%)`;
            pages[curIdx].style.filter = 'blur(15px)';
            pages[curIdx].style.opacity = '0';

            setTimeout(() => {
                pages[curIdx].classList.remove('active');
                pages[idx].style.transition = 'none';
                pages[idx].style.transform = `translateX(${dir * 100}%)`;
                pages[idx].style.filter = 'blur(15px)';
                pages[idx].style.opacity = '0';
                void pages[idx].offsetHeight;

                requestAnimationFrame(() => {
                    pages[idx].style.transition = 'all 450ms cubic-bezier(0.2, 0.8, 0.2, 1)';
                    pages[idx].style.transform = 'translateX(0)';
                    pages[idx].style.filter = 'blur(0)';
                    pages[idx].style.opacity = '1';
                    pages[idx].classList.add('active');
                    if (container) container.scrollTop = 0;
                    updatePanelOverflowHint();
                });
                state.pageIndex = idx;
                // Honest progress: mark this (panel, page) pair as seen.
                // Distinct only — back-swiping doesn't add new units.
                previewMarkPageSeen(state.panelIndex, idx);
                updateDots();
                updatePanelButton();

                setTimeout(() => {
                    pages[idx].style.transition = '';
                    pages[idx].style.transform = '';
                    pages[idx].style.filter = '';
                    pages[idx].style.opacity = '';
                    state.isAnimating = false;
                }, 500);
            }, 50);
        }

        function nextPanel() {
            if (state.panelIndex >= PANELS.length - 1) {
                showBreakScreen();
                return;
            }
            state.isAnimating = true;
            const card = document.getElementById('panel-card');
            if (card) {
                card.classList.add('bounce');
                setTimeout(() => card.classList.remove('bounce'), 450);
            }

            const content = document.getElementById('panel-content');
            if (content) {
                content.style.transition = 'all 400ms ease-in';
                content.style.transform = 'translateX(-100%)';
                content.style.filter = 'blur(15px)';
                content.style.opacity = '0';
            }

            setTimeout(() => {
                state.panelIndex++;
                state.pageIndex = 0;
                // Honest progress: a brand-new panel's page 0 just became
                // visible. Counted as one distinct (panel, page) pair.
                previewMarkPageSeen(state.panelIndex, 0);
                renderPanel();
                if (content) {
                    content.style.transition = 'none';
                    content.style.transform = 'translateX(100%)';
                    void content.offsetHeight;
                    requestAnimationFrame(() => {
                        content.style.transition = 'all 500ms cubic-bezier(0.2, 0.8, 0.2, 1)';
                        content.style.transform = 'translateX(0)';
                        content.style.filter = 'blur(0)';
                        content.style.opacity = '1';
                    });
                }
                setTimeout(() => state.isAnimating = false, 500);
            }, 400);
        }

        function prevPanel() {
            state.isAnimating = true;
            const card = document.getElementById('panel-card');
            if (card) {
                card.classList.add('bounce');
                setTimeout(() => card.classList.remove('bounce'), 450);
            }

            const content = document.getElementById('panel-content');
            if (content) {
                content.style.transition = 'all 400ms ease-in';
                content.style.transform = 'translateX(100%)';
                content.style.filter = 'blur(15px)';
                content.style.opacity = '0';
            }

            setTimeout(() => {
                state.panelIndex--;
                state.pageIndex = PANELS[state.panelIndex].pages.length - 1;
                // Cover the case where the user jumps backward to a panel/page
                // they've already seen — Set semantics make this a no-op, but
                // landing on an unseen position (e.g. last page of an earlier
                // panel they skipped over) does count.
                previewMarkPageSeen(state.panelIndex, state.pageIndex);
                renderPanel();
                if (content) {
                    content.style.transition = 'none';
                    content.style.transform = 'translateX(-100%)';
                    void content.offsetHeight;
                    requestAnimationFrame(() => {
                        content.style.transition = 'all 500ms cubic-bezier(0.2, 0.8, 0.2, 1)';
                        content.style.transform = 'translateX(0)';
                        content.style.filter = 'blur(0)';
                        content.style.opacity = '1';
                    });
                }
                setTimeout(() => state.isAnimating = false, 500);
            }, 400);
        }

        function updateDots() {
            const dots = document.querySelectorAll('.dot');
            dots.forEach((d, i) => d.classList.toggle('active', i === state.pageIndex));
        }

        /* ── STAGE 5 GAME BREAK ──────────────────────────────────── */

        const GB_ADAPTIVE_QUIZ = [
            {id:'A1',tier:'easy',bloom:'L2',pisa:'L1',prompt:'Yeching: x\u00b2 = 81',answer:'\u00b19',work:'x = \u00b1\u221a81 = \u00b19'},
            {id:'A2',tier:'easy',bloom:'L2',pisa:'L1',prompt:'Yeching: x\u00b2 = 0',answer:'0',work:'x\u00b2 = 0 \u2192 x = 0'},
            {id:'A3',tier:'easy',bloom:'L2',pisa:'L2',prompt:'Yeching: x\u00b2 + 16 = 0',answer:"haqiqiy ildiz yo'q",work:'x\u00b2 = \u201316 < 0 \u2192 no real roots'},
            {id:'A4',tier:'medium',bloom:'L3',pisa:'L2',prompt:'Yeching: x\u00b2 = 20',answer:'\u00b12\u221a5',work:'x = \u00b1\u221a20 = \u00b1\u221a(4\u00b75) = \u00b12\u221a5'},
            {id:'A5',tier:'medium',bloom:'L3',pisa:'L2',prompt:'Yeching: x\u00b2 \u2013 49 = 0',answer:'\u00b17',work:'(x \u2013 7)(x + 7) = 0 \u2192 x = \u00b17'},
            {id:'A6',tier:'medium',bloom:'L3',pisa:'L3',prompt:'Yeching: x\u00b2 + 5x + 6 = 0',answer:'\u20132 va \u20133',work:'p+q=5, pq=6 \u2192 (2,3); (x+2)(x+3)=0'},
            {id:'A7',tier:'hard',bloom:'L3',pisa:'L3',prompt:'Yeching: x\u00b2 + 10x \u2013 24 = 0',answer:'2 va \u201312',work:'p+q=10, pq=\u201324 \u2192 (\u20132,12); (x\u20132)(x+12)=0'},
            {id:'A8',tier:'hard',bloom:'L4',pisa:'L3',prompt:'Yeching: x\u00b2 \u2013 3x \u2013 10 = 0',answer:'5 va \u20132',work:'p+q=\u20133, pq=\u201310 \u2192 (\u20135,2); (x\u20135)(x+2)=0'}
        ];

        const GB_WHY_CHAIN = [
            {id:'C1',bloom:'L3',pisa:'L3',chain:[
                {level:1,probe:"Nega `a` nolga teng bo'lishi mumkin emas?",expect:"Chunki u holda x\u00b2 yo'qoladi."},
                {level:2,probe:"Agar x\u00b2 yo'qolsa, tenglama qanday ko'rinishga keladi?",expect:'Chiziqli tenglama (bx + c = 0).'},
                {level:3,probe:'Demak, tenglamani aynan "kvadrat" qiladigan narsa nima?',expect:'x\u00b2 hadining mavjudligi \u2014 ikkinchi daraja.'}
            ],invariant:'x\u00b2 is what defines a quadratic.'},
            {id:'C2',bloom:'L4',pisa:'L3',chain:[
                {level:1,probe:'Nega kvadrat tenglama odatda ikkita javobga ega?',expect:'Musbat va manfiy son bir xil musbatga kvadrat boladi.'},
                {level:2,probe:'Qaysi amal bu "ikkilikni" hosil qiladi?',expect:"Kvadratga ko'tarish \u2014 u belgini yashiradi."},
                {level:3,probe:"Unda x va x\u00b2 o'rtasida qanday bog'liqlik bor?",expect:'x\u00b2 x ning belgisini bilmaydi. Qaytarish uchun \u00b1 kerak.'}
            ],invariant:'Squaring destroys sign; reversing requires \u00b1.'},
            {id:'C3',bloom:'L4',pisa:'L4',chain:[
                {level:1,probe:'Agar tortburchak masalasida x = 2 va x = \u201312 chiqsa, nega \u201312 tashlanadi?',expect:'Uzunlik manfiy bolmaydi.'},
                {level:2,probe:'Ammo ikkala javob matematik togri. Farqi qayerda?',expect:'Matematika kontekstni bilmaydi; haqiqiy olamda fizik cheklovlar bor.'},
                {level:3,probe:'Tenglama va masala ortasida qanday bogliqlik?',expect:'Tenglama matematik javoblarni beradi; kontekst qay biri haqiqiy ekanligini filtrlaydi.'}
            ],invariant:'Math-world and problem-world are separate; context filters.'}
        ];

        const GB_MEMORY_MATCH = [
            {a:'a',b:'bosh koeffitsiyent',confirmQ:'x\u00b2 oldidagi son nima deyiladi?',correct:'bosh koeffitsiyent'},
            {a:'b',b:'ikkinchi koeffitsiyent',confirmQ:'x oldidagi son nima?',correct:'ikkinchi koeffitsiyent'},
            {a:'c',b:'ozod had',confirmQ:'Harfsiz sonning nomi?',correct:'ozod had'},
            {a:'ildiz',b:"tenglamani to'g'ri qiladigan qiymat",confirmQ:'Ildiz nima?',correct:"tenglamani to'g'ri qiladigan qiymat"},
            {a:'ax\u00b2 + bx + c = 0',b:'standart shakl',confirmQ:"Kvadrat tenglamaning asosiy ko'rinishi?",correct:'standart shakl'},
            {a:'\u00b1',b:'plyus yoki minus',confirmQ:'\u00b1 belgisi nimani anglatadi?',correct:'plyus yoki minus'},
            {a:'x\u00b2 = d, d > 0',b:'2 ta haqiqiy ildiz',confirmQ:'d musbat bolsa, nechta ildiz?',correct:'2 ta haqiqiy ildiz'},
            {a:'x\u00b2 = d, d < 0',b:"haqiqiy ildiz yo'q",confirmQ:'d manfiy bolsa, nechta haqiqiy ildiz?',correct:"haqiqiy ildiz yo'q"}
        ];

        const GB_TILE_MATCH = __GB_TILE_MATCH__;

        const GB_PUZZLE_LOCK = [];

        const GB_MYSTERY_BOX = [];

        const GB_TTT = [];

        const GB_SENTENCE_FILL = __GB_SENTENCE_FILL__;

        const GB_MEMORY_PALACE = __GB_MEMORY_PALACE__;

        let gbState = {
            subGame: 0,
            aq: { shown:0, correct:0, currentItem:null, currentTier:'easy', captureOk:false, answered:false },
            wc: { chainIdx:0, levelIdx:0, retries:0 },
            mm: { tiles:[], flipped:[], matched:0, pendingPair:null, busy:false, complete:false },
            pl: { size:3, cells:[], emptyIdx:0, tiles:[], selected:null, total:0, correct:0, wrongCount:0, complete:false, busy:false },
            mb: { boxes:[], opened:[], idx:-1, phase:'select', labels:[], pickedLabel:'', idCorrect:null, ansCorrect:null, complete:false, busy:false },
            ttt: { sessionId:null, board:Array(9).fill(''), games:[], gameNum:0, draws:0, losses:0, correct:0, pendingCellIdx:-1, currentItemIdx:0, currentItemId:null, phase:'await-tap', busy:false, complete:false, winLine:null },
            sf: { idx:0, mode:'word_bank', selectedBlank:0, blanks:[], xp:0, pendingFinalize:false, complete:false, busy:false },
            tm: { tiles:[], pairsTotal:0, matched:0, wrong:0, streak:0, xp:0, selectedLeft:null, busy:false, complete:false, startedAt:null, outcome:null, sessionId:null },
            // Memory Palace (gb-panel-mp, sub-slot 7) — Method of Loci 4-step flow.
            mp: {
                step: 1,                  // 1..4 (5 = result)
                selectedPalace: null,     // palace object once chosen
                filteredPalaces: [],      // tier-filtered subset of GB_MEMORY_PALACE.palaces
                conceptIndex: 0,          // pointer into concepts[] during Step 2
                placements: [],           // [{location_idx, concept_id}] (length = locations.length)
                walkIndex: 0,             // pointer during Step 3
                recallIndex: 0,           // pointer during Step 4
                recallResults: [],        // [{location_idx, picked_concept_id, is_correct, elapsed_ms}]
                recallStartAt: null,      // ms timestamp per question
                recallOptions: [],        // shuffled MC options for current Step 4 question
                hintsUsed: 0,
                result: null,             // server response from gbMPSubmitSession
                sessionId: null,          // minted on init
                busy: false,
                complete: false,
            }
        };

        // ── Registry-driven game-break order ─────────────────────────────

        // Every Phase-3 game is OPTIONAL: it appears only when its content
        // array has items. The runtime walks gbActiveGameOrder() in order,
        // skipping any empty slot. If all five are empty, Stage 5 is skipped
        // entirely from startStage5. This rule applies to every future game
        // added below — never inject placeholder content for empty games.
        function gbIsGrade8MathDemo() {
            const ctx = window.NETS_CTX || {};
            const subject = String(ctx.subject || '').toLowerCase().trim();
            const grade = Number(ctx.grade);
            return grade === 8 && (subject === 'math-algebra' || subject === 'geometriya-g7-11');
        }

        function gbDemoSkippedGames() {
            return gbIsGrade8MathDemo() ? new Set(['aq', 'wc', 'pl']) : new Set();
        }

        function gbActiveGameOrder() {
            const list = [];
            const skipped = gbDemoSkippedGames();
            if (!skipped.has('aq') && Array.isArray(GB_ADAPTIVE_QUIZ) && GB_ADAPTIVE_QUIZ.length > 0)
                list.push({ id: 'aq', sub: 0, init: gbInitAQ, panel: 'gb-panel-aq', label: 'Adaptive Quiz', labelKey: 'game.aq', setupBtn: gbSetButtonForAQ });
            if (!skipped.has('wc') && Array.isArray(GB_WHY_CHAIN) && GB_WHY_CHAIN.length > 0)
                list.push({ id: 'wc', sub: 1, init: gbInitWC, panel: 'gb-panel-wc', label: 'Sentence Fill', labelKey: 'game.wc', setupBtn: gbSetButtonForWC });
            if (!skipped.has('tm') && Array.isArray(GB_TILE_MATCH) && GB_TILE_MATCH.length > 0)
                list.push({ id: 'tm', sub: 2, init: gbInitTM, panel: 'gb-panel-tm', label: 'Tile Match', labelKey: 'game.tm', setupBtn: null });
            if (!skipped.has('pl') && Array.isArray(GB_PUZZLE_LOCK) && GB_PUZZLE_LOCK.length > 0)
                list.push({ id: 'pl', sub: 3, init: gbInitPL, panel: 'gb-panel-pl', label: 'Puzzle Lock', labelKey: 'game.pl', setupBtn: null });
            if (!skipped.has('mb') && Array.isArray(GB_MYSTERY_BOX) && GB_MYSTERY_BOX.length > 0)
                list.push({ id: 'mb', sub: 4, init: gbInitMB, panel: 'gb-panel-mb', label: 'Mystery Box', labelKey: 'game.mb', setupBtn: null });
            if (!skipped.has('ttt') && Array.isArray(GB_TTT) && GB_TTT.length > 0)
                list.push({ id: 'ttt', sub: 5, init: gbInitTTT, panel: 'gb-panel-ttt', label: 'Tic Tac Toe', labelKey: 'game.ttt', setupBtn: null });
            if (!skipped.has('sf') && Array.isArray(GB_SENTENCE_FILL) && GB_SENTENCE_FILL.length > 0)
                list.push({ id: 'sf', sub: 6, init: gbInitSF, panel: 'gb-panel-sf', label: 'Sentence Fill', labelKey: 'game.sf', setupBtn: gbSetButtonForSF });
            // Memory Palace (sub-slot 7). Gate on non-null wire + ≥1 palace + ≥3 concepts
            // (mirrors TM/SF/TTT empty-content gating). content lives in GB_MEMORY_PALACE.
            if (!skipped.has('mp') && GB_MEMORY_PALACE && Array.isArray(GB_MEMORY_PALACE.palaces) && GB_MEMORY_PALACE.palaces.length > 0
                && Array.isArray(GB_MEMORY_PALACE.concepts) && GB_MEMORY_PALACE.concepts.length >= 3)
                list.push({ id: 'mp', sub: 7, init: gbInitMP, panel: 'gb-panel-mp', label: 'Memory Palace', labelKey: 'game.mp', setupBtn: null });
            return list;
        }

        function gbActiveGameLabels() {
            return gbActiveGameOrder().map(g => g.label);
        }

        function gbIsLastGame(currentSub) {
            const order = gbActiveGameOrder();
            const idx = order.findIndex(g => g.sub === currentSub);
            return idx >= 0 && idx === order.length - 1;
        }

        function gbAdvanceFromGame(currentSub, currentPanelId) {
            const order = gbActiveGameOrder();
            const idx = order.findIndex(g => g.sub === currentSub);
            if (idx < 0 || idx >= order.length - 1) {
                // No more games in the registry — exit Stage 5.
                // Sentinel 99 (not 6) — slot 6 is now Sentence Fill (gb-panel-sf).
                gbState.subGame = 99;
                gbExitToStage6();
                return;
            }
            const next = order[idx + 1];
            gbState.subGame = next.sub;
            gbUpdateProgress(idx + 1);
            // Timing fix: the previous sub-game panel must visually close
            // BEFORE the announcement card appears. The pre-fix flow showed
            // the next-phase name overlaying the still-active previous
            // panel — students saw two phases at once. Mirrors the
            // startStage6 / showConsolidationScreen pattern: fade out the
            // outgoing content first, THEN announce, THEN slide the new
            // panel in. Inner ordering remains playPhaseAnnouncement first,
            // then gbTransition, then the next game's init (the
            // test_gb_advance_from_game_plays_announcement_before_transition
            // regression test pins this).
            const fromPanel = document.getElementById(currentPanelId);
            const proceed = () => {
                playPhaseAnnouncement(next.labelKey || ('game.' + next.id), () => {
                    gbTransition(currentPanelId, next.panel, () => {
                        next.init();
                        if (next.setupBtn) {
                            next.setupBtn();
                        } else {
                            btn.classList.remove('pulse','state-pill','state-line');
                            btn.classList.add('state-line');
                            if (btnText) btnText.style.opacity = '0';
                        }
                    });
                });
            };
            if (fromPanel) {
                fromPanel.style.transition = 'opacity 280ms ease, filter 280ms ease';
                fromPanel.style.opacity = '0';
                fromPanel.style.filter = 'blur(6px)';
                setTimeout(proceed, 290);
            } else {
                proceed();
            }
        }

        function startStage5() {
            if (state.isAnimating) return;
            const order = gbActiveGameOrder();
            if (order.length === 0) {
                // No games authored anywhere — skip Stage 5 entirely.
                // Treat as no-op for completion; nothing to do here.
                gbExitToStage6();
                return;
            }
            state.isAnimating = true;
            btn.classList.remove('pulse','state-pill','state-line');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            document.querySelectorAll('.screen.active').forEach(s => s.classList.remove('active'));
            setStage(5);
            // Real completion: 1 unit per sub-game (Adaptive Quiz, Memory
            // Match, Pattern Lock, Math Brawl, …). gbUpdateProgress(idx)
            // below mirrors the live index into completionState.
            setPhaseRequired('gameBreaks', order.length);
            const first = order[0];
            gbState.subGame = first.sub;
            const firstPanel = document.getElementById(first.panel);
            if (firstPanel) {
                // Strip slide-in classes baked into MM/PL/MB HTML — otherwise
                // .enter-right keeps the panel translated 100% off-screen even
                // with .active applied. AQ has no enter-right so this is a
                // no-op when AQ is the first game.
                firstPanel.classList.remove('enter-right', 'exit-left');
                firstPanel.classList.add('active');
            }
            const s5 = document.getElementById('screen-5');
            if (s5) s5.classList.add('active');
            gbUpdateProgress(0);

            // Phase-intro announcement (mirrors Memory Sprint pattern): show the
            // intro card centered for ~1.2s, fade out (700ms), then reveal the
            // game shell instantly — no opacity overlap.
            //
            // Defer first.init() until AFTER the announcement: AQ's init arms
            // the bottom button ("Javobni tekshirish"), which would otherwise
            // appear during the card animation. Mirrors showReadingScreen's
            // deferral of renderReading().
            const gbShell = document.getElementById('gb-shell');
            if (gbShell) { gbShell.style.transition = 'none'; gbShell.style.opacity = '0'; }
            playPhaseIntro('gb-phase-center-card', () => {
                if (gbShell) { gbShell.style.transition = 'opacity 300ms ease'; gbShell.style.opacity = '1'; }
                first.init();
                if (first.setupBtn) { first.setupBtn(); }
                // Else: init function (MM/PL/MB) already set the button to inert.
                state.isAnimating = false;
            });
        }

        // Generic phase-intro animation runner. Shows the card for ~1.2s, fades
        // out 700ms, then calls onDone at 1950ms. Used by Stage 5 (Game Breaks)
        // and Reading. Pattern matches startMemorySprintPhase exactly.
        function playPhaseIntro(cardId, onDone) {
            // PR #211 root-cause fix — wave2 phases (reading/consolidation/
            // reflection) gate their button morph on this callback. If the
            // setTimeout-driven cleanup ever swallows an exception or the
            // timer is dropped, the shared morphing #action-button stays in
            // .state-line (4px invisible bar) and students get stranded.
            // Guarantee onDone fires AT MOST ONCE, and ALWAYS, even if
            // cleanup throws or the card was removed mid-animation.
            let fired = false;
            const fire = () => {
                if (fired) return;
                fired = true;
                try { onDone && onDone(); } catch (e) {
                    // Swallow downstream errors so a buggy caller can't
                    // re-introduce the stuck-button state. Log for forensics.
                    try { console.warn('[playPhaseIntro] onDone threw:', e); } catch (_) {}
                }
            };
            const card = document.getElementById(cardId);
            if (!card) { fire(); return; }
            try {
                card.style.display = '';
                card.style.animation = '';
                // requestAnimationFrame to ensure the browser paints with .show absent
                // before we add it — guarantees the opacity transition runs.
                requestAnimationFrame(() => {
                    try { card.classList.add('show'); } catch (_) {}
                });
                setTimeout(() => {
                    try { card.style.animation = 'phaseIntroFadeOut 700ms ease forwards'; } catch (_) {}
                }, 1200);
                setTimeout(() => {
                    try {
                        card.classList.remove('show');
                        card.style.display = 'none';
                        card.style.animation = '';
                    } catch (_) {}
                    fire();
                }, 1950);
                // Watchdog backstop — if the 1950ms timer is throttled away
                // (background tab) or dropped, fire onDone at 4000ms so the
                // wave2 button always reaches .state-pill within ~4s of the
                // phase transition. The `fired` guard makes this idempotent
                // with the normal-path setTimeout above.
                setTimeout(fire, 4000);
            } catch (e) {
                // Setup itself failed — fire immediately so the caller can
                // still flip the button visible.
                try { console.warn('[playPhaseIntro] setup threw:', e); } catch (_) {}
                fire();
            }
        }

        // Bug #4: phase announcement card retrofit. Single shared card whose
        // text comes from RUNTIME_LABELS so it speaks the homework's language.
        // Used for sub-game starts inside Stage 5 plus the entries into
        // Real-Life / Consolidation / Reflection. Boss has its own bespoke
        // intro card and is intentionally skipped here. Existing static cards
        // (gb-phase-center-card, reading-phase-center-card) keep their callers.
        function playPhaseAnnouncement(labelKey, onDone) {
            const card = document.getElementById('phase-announce-card');
            if (!card) { onDone && onDone(); return; }
            const textEl = document.getElementById('phase-announce-text');
            if (textEl) {
                const resolved = (typeof labelKey === 'string' && labelKey)
                    ? RT(labelKey) : '';
                textEl.textContent = resolved || labelKey || '';
            }
            playPhaseIntro('phase-announce-card', onDone);
        }

        function gbUpdateProgress(idx) {
            const labels = gbActiveGameLabels();
            const total = labels.length;
            const labelEl = document.getElementById('gb-plabel');
            if (labelEl) {
                labelEl.textContent = labels[idx]
                    ? ((idx + 1) + '/' + total + ' ' + labels[idx])
                    : '';
            }
            for (let i = 1; i <= 6; i++) {
                const d = document.getElementById('gb-pd-' + i);
                if (!d) continue;
                if (i > total) {
                    d.style.display = 'none';
                    d.className = 'gb-pdot';
                } else {
                    d.style.display = '';
                    d.className = 'gb-pdot';
                    if (i - 1 < idx) d.classList.add('done');
                    else if (i - 1 === idx) d.classList.add('active');
                }
            }
            // Mirror sub-game index into the top-level completion model so the
            // dot-4 (Game Breaks) segment partial-fills as the student clears
            // Adaptive Quiz → Memory Match → Pattern Lock → Math Brawl.
            // `idx` is 0-based; treat "currently on game N" as N-prior games done.
            setPhaseProgress('gameBreaks', Math.max(0, idx), total > 0 ? total : 1);
        }

        function gbSetButtonForAQ() {
            btn.classList.remove('pulse','state-pill','state-line');
            btn.classList.add('state-pill');
            setBtnText(RT('btn.check_answer'));
            btn.classList.add('pulse');
        }

        function gbSetButtonForWC() {
            btn.classList.remove('pulse','state-pill','state-line');
            btn.classList.add('state-pill');
            setBtnText(RT('btn.submit_answer'));
            btn.classList.add('pulse');
        }

        function gbSetButtonNext(text, hidden) {
            // The optional `hidden` flag visually conceals the morph button
            // while preserving its DOM (text, aria-label) so screen readers
            // still announce the prompt. Used by Tile Match dock prompts
            // ("Juftlikni tanlang" / "Ma'noni tanlang") which are pure
            // labels — the user can't progress by tapping the button,
            // only by tapping tiles. Showing a tappable-looking pill is
            // misleading there. The flag is reset on EVERY call to this
            // helper, so the button auto-reappears the moment any phase
            // calls gbSetButtonNext('<next>') (e.g. gbTMFinish).
            btn.classList.remove('pulse','state-pill','state-line','tm-dock-hidden');
            btn.classList.add('state-pill');
            setBtnText(text || RT('btn.next'));
            btn.classList.add('pulse');
            if (hidden) btn.classList.add('tm-dock-hidden');
        }

        function gbHandleAction() {
            if (state.isAnimating) return;
            if (gbState.subGame === 99) { gbExitToStage6(); return; }
            if (gbState.subGame === 7) {
                if (gbState.mp && gbState.mp.complete) { gbAdvanceFromGame(7, 'gb-panel-mp'); return; }
                gbMPAction(); return;
            }
            if (gbState.subGame === 6) {
                if (gbState.sf && gbState.sf.complete) { gbAdvanceFromGame(6, 'gb-panel-sf'); return; }
                gbSFAction(); return;
            }
            if (gbState.subGame === 5) {
                if (gbState.ttt && gbState.ttt.complete) { gbAdvanceFromGame(5, 'gb-panel-ttt'); return; }
                gbTTTAction(); return;
            }
            if (gbState.subGame === 4) {
                if (gbState.mb && gbState.mb.complete) { gbAdvanceFromGame(4, 'gb-panel-mb'); return; }
                gbMBAction(); return;
            }
            if (gbState.subGame === 3) {
                if (gbState.pl && gbState.pl.complete) { gbAdvanceFromGame(3, 'gb-panel-pl'); return; }
                // PR A 2026-05-07: linear stepper — the active step is always
                // ready, so the CTA always dispatches to gbPLAction. The old
                // pl.selected gate (waiting for a tile click) no longer applies.
                gbPLAction(); return;
            }
            if (gbState.subGame === 2) {
                if (gbState.tm && gbState.tm.complete) { gbAdvanceFromGame(2, 'gb-panel-tm'); return; }
                gbTMAction(); return;
            }
            if (gbState.subGame === 1) {
                const inv = document.getElementById('gb-wc-invariant');
                if (inv && inv.classList.contains('show')) { gbWCNextChain(); return; }
                gbWCAction(); return;
            }
            if (gbState.subGame === 0) { gbAQAction(); return; }
        }

        function gbTransition(fromId, toId, onDone) {
            state.isAnimating = true;
            const from = document.getElementById(fromId);
            const to = document.getElementById(toId);
            if (from) {
                from.style.transition = 'transform 380ms cubic-bezier(0.4,0,0.2,1), opacity 380ms ease, filter 380ms ease';
                from.style.transform = 'translateX(-100%)';
                from.style.filter = 'blur(12px)';
                from.style.opacity = '0';
            }
            setTimeout(() => {
                if (from) { from.classList.remove('active'); from.style.cssText = ''; }
                if (to) {
                    to.classList.remove('enter-right', 'exit-left');
                    to.style.cssText = 'transform:translateX(100%);filter:blur(12px);opacity:0;';
                    void to.offsetHeight;
                    requestAnimationFrame(() => {
                        to.style.transition = 'transform 380ms cubic-bezier(0.4,0,0.2,1), opacity 380ms ease, filter 380ms ease';
                        to.style.transform = 'translateX(0)';
                        to.style.filter = 'blur(0)';
                        to.style.opacity = '1';
                        to.classList.add('active');
                    });
                }
                setTimeout(() => {
                    if (to) to.style.cssText = '';
                    state.isAnimating = false;
                    if (onDone) onDone();
                }, 420);
            }, 380);
        }

        function gbInitAQ() {
            const aq = gbState.aq;
            aq.shown = 0; aq.correct = 0; aq.currentTier = 'easy'; aq.captureOk = false; aq.answered = false;
            aq.shownIds = [];
            // Reset visual scaffolding: result-box hidden, status pill back to step 1,
            // upload-gate hidden, textarea cleared. New copy comes from i18n keys
            // (RT) so the runtime language switch is preserved across phases.
            const rb = document.getElementById('aq-result-box');
            if (rb) { rb.classList.remove('show', 'wrong'); }
            const rt = document.getElementById('aq-result-title'); if (rt) rt.textContent = '';
            const rtxt = document.getElementById('aq-result-text'); if (rtxt) rtxt.textContent = '';
            const gate = document.getElementById('aq-upload-gate');
            if (gate) gate.classList.remove('show');
            const sp = document.getElementById('aq-status-pill');
            if (sp) { sp.classList.remove('is-correct', 'is-wrong'); sp.textContent = RT('aq.status_step1'); }
            const ta = document.getElementById('gb-aq-textarea');
            if (ta) ta.value = '';
            const files = document.getElementById('aq-files');
            if (files) files.innerHTML = '';
            gbAQShowNext();
        }

        // Forward padding-gap clicks on the answer card to the textarea. Without
        // this, taps in the ~10px gap between the "Javob" heading and the
        // textarea border land on the parent <section> and don't focus the
        // input — students felt this as a dead band at the top of the textbox
        // (regression 2026-05-02). Skips clicks that already hit an interactive
        // child (the upload drop-zone, the textarea itself).
        document.addEventListener('DOMContentLoaded', () => {
            const card = document.querySelector('.aq-answer-card');
            const ta = document.getElementById('gb-aq-textarea');
            if (!card || !ta) return;
            card.addEventListener('click', (e) => {
                if (e.target === ta) return;
                if (e.target.closest('button, a, [role="button"], input, select, textarea')) return;
                ta.focus();
            });
        });

        function gbAQPickItem() {
            const aq = gbState.aq;
            if (!aq.shownIds) aq.shownIds = [];
            const tier = aq.currentTier;
            const idOf = q => q.id || (q.prompt || '').slice(0, 40);
            const inTier  = GB_ADAPTIVE_QUIZ.filter(q => q.tier === tier);
            const fresh   = inTier.filter(q => !aq.shownIds.includes(idOf(q)));
            const pool    = fresh.length ? fresh
                          : (GB_ADAPTIVE_QUIZ.filter(q => !aq.shownIds.includes(idOf(q))).length
                              ? GB_ADAPTIVE_QUIZ.filter(q => !aq.shownIds.includes(idOf(q)))
                              : (inTier.length ? inTier : GB_ADAPTIVE_QUIZ));
            const item = pool[Math.floor(Math.random() * pool.length)];
            if (item) aq.shownIds.push(idOf(item));
            return item || GB_ADAPTIVE_QUIZ[0];
        }

        function gbAQShowNext() {
            const aq = gbState.aq;
            if (aq.shown >= 5) { gbAQFinish(); return; }
            // Clear any pending auto-advance timer from the previous question.
            if (aq._autoAdvanceTimer) { clearTimeout(aq._autoAdvanceTimer); aq._autoAdvanceTimer = null; }
            const item = gbAQPickItem();
            aq.currentItem = item;
            // Notebook Capture is per-item. When item.capture is false, pre-satisfy
            // the gate and hide the camera UI so the student isn't forced through it.
            aq.captureOk = !item.capture;
            aq.answered = false;
            // Topbar counter: "Savol N/5" — reuse aq.question_of for the localized "Q" label.
            const qNow = document.getElementById('aq-q-now');
            if (qNow) qNow.textContent = String(aq.shown + 1);
            const qTotal = document.getElementById('aq-q-total');
            if (qTotal) qTotal.textContent = '5';
            const cntLabel = document.getElementById('aq-count-label');
            if (cntLabel) cntLabel.textContent = RT('aq.question_of');
            // Phase label + dots: light up the current Stage-5 sub-game ordinal.
            try {
                const order = (typeof gbActiveGameOrder === 'function') ? gbActiveGameOrder() : [];
                const total = order.length;
                let idx = 0;
                for (let i = 0; i < total; i++) { if (order[i] && order[i].id === 'aq') { idx = i; break; } }
                const phaseLabel = document.getElementById('aq-phase-label');
                if (phaseLabel) phaseLabel.textContent = (idx + 1) + '/' + (total || 1) + ' Adaptive Quiz';
                const dotsHost = document.getElementById('aq-dots');
                if (dotsHost) {
                    const dots = dotsHost.querySelectorAll('span');
                    for (let i = 0; i < dots.length; i++) {
                        dots[i].classList.toggle('active', i === idx);
                    }
                }
            } catch (_) { /* tolerate any registry hiccups */ }
            // Tier headline + eyebrow: i18n-driven copy + tier color class.
            const tierKey = 'aq.tier_' + (item.tier || 'easy');
            const tierHead = document.getElementById('aq-tier-headline');
            if (tierHead) {
                tierHead.textContent = RT(tierKey);
                tierHead.className = 'aq-tier-headline tier-' + (item.tier || 'easy');
            }
            const tierEyebrow = document.getElementById('aq-tier-eyebrow');
            if (tierEyebrow) tierEyebrow.textContent = (item.tier || 'easy').toUpperCase();
            // Question text — keep #gb-aq-question ID untouched (existing innerHTML write).
            const qEl = document.getElementById('gb-aq-question');
            // innerHTML — adaptive quiz prompt may contain inline images/SVGs/bold/italic.
            // Format inline MC option markers ("A)", "B)", "C)", "D)") onto separate
            // lines when authors include them inside the prompt text. Looks for a
            // whitespace boundary so mid-word matches ("VitaminA)…") aren't broken.
            const formattedPrompt = (item.prompt || '').replace(/\s+([A-D]\))/g, '<br>$1');
            if (qEl) qEl.innerHTML = formattedPrompt;
            const tags = document.getElementById('gb-aq-tags');
            if (tags) tags.textContent = '[Bloom: ' + item.bloom + ' | PISA: ' + item.pisa + ']';
            // Answer-card copy from i18n.
            const ansLbl = document.getElementById('aq-answer-label');
            if (ansLbl) ansLbl.textContent = RT('aq.answer_label');
            const ansHelp = document.getElementById('aq-answer-help');
            if (ansHelp) ansHelp.textContent = RT('aq.answer_help');
            // Textarea reset.
            const inp = document.getElementById('gb-aq-textarea');
            if (inp) { inp.value = ''; inp.disabled = false; inp.style.borderColor = ''; }
            // Upload-gate visibility per item.capture.
            const gate = document.getElementById('aq-upload-gate');
            if (gate) gate.classList.toggle('show', !!item.capture);
            const upStrong = document.getElementById('aq-upload-strong');
            if (upStrong) upStrong.textContent = RT('aq.upload_drop_label');
            const upSub = document.getElementById('aq-upload-sub');
            if (upSub) upSub.textContent = RT('aq.upload_subtitle');
            const drop = document.getElementById('aq-drop');
            if (drop) drop.textContent = RT('aq.upload_solution');
            const files = document.getElementById('aq-files');
            if (files) files.innerHTML = '';
            // Status pill back to "Step 1".
            const sp = document.getElementById('aq-status-pill');
            if (sp) { sp.classList.remove('is-correct', 'is-wrong'); sp.textContent = RT('aq.status_step1'); }
            // Result-box cleared.
            const rb = document.getElementById('aq-result-box');
            if (rb) rb.classList.remove('show', 'wrong');
            const rt = document.getElementById('aq-result-title'); if (rt) rt.textContent = '';
            const rtxt = document.getElementById('aq-result-text'); if (rtxt) rtxt.textContent = '';
            gbSetButtonForAQ();
        }

        function gbAQCapture() {
            if (gbState.aq.answered) return;
            gbState.aq.captureOk = true;
            // Status pill flips to "upload done"; drop the gate's drop button into a
            // single "file pill" affordance to confirm the action visually. Toast is
            // optional — only fires if the host element is in the DOM.
            const sp = document.getElementById('aq-status-pill');
            if (sp) { sp.classList.remove('is-wrong'); sp.textContent = RT('aq.status_upload_done'); }
            const files = document.getElementById('aq-files');
            if (files) {
                files.innerHTML = '';
                const pill = document.createElement('div');
                pill.className = 'aq-file-pill';
                pill.innerHTML = '<span>' + RT('aq.solution_uploaded') + '</span><small>OK</small>';
                files.appendChild(pill);
            }
            gbAQToast(RT('aq.solution_uploaded'));
        }

        function gbAQToast(msg) {
            const t = document.getElementById('aq-toast');
            if (!t) return;
            t.textContent = msg || '';
            t.classList.add('show');
            if (t._timer) clearTimeout(t._timer);
            t._timer = setTimeout(() => { t.classList.remove('show'); t._timer = null; }, 2200);
        }

        // List mirrors server/services/language.py — keep them in sync. Used to decide
        // whether AQ goes through deterministic string match (default, fast, no AI cost)
        // or through the AI grader (language subjects, paraphrase-aware).
        const LANGUAGE_SUBJECTS_RUNTIME = new Set([
            'english', 'ona-tili', 'rus-tili',
            'ingliz-tili', 'ingliz-tili-g1-11', 'ona-tili-g1-11', 'rus-tili-g1-11',
        ]);

        function gbIsLanguageSubject() {
            const s = (window.NETS_CTX && (NETS_CTX.subject || '')).toLowerCase().trim();
            return LANGUAGE_SUBJECTS_RUNTIME.has(s);
        }

        // AC-01: Math answer normalization. Mirror of server/services/math_normalize.py.
        // Both implementations must produce identical canonical strings — the test
        // suite tests/test_runtime_math_normalize_js.py runs JS via PyExecJS to verify.
        // Used by gbAQAction's deterministic compare path so equivalent forms match:
        //   α/alfa/alpha, tg/tan, ctg/cot, U+2212/-, decimal comma/dot,
        //   "sin B = 0,6" → "0.6", degree markers stripped, internal spaces collapsed.
        const _MATH_GREEK = {
            'α':'alpha','β':'beta','γ':'gamma','δ':'delta','ε':'epsilon','ζ':'zeta',
            'η':'eta','θ':'theta','ι':'iota','κ':'kappa','λ':'lambda','μ':'mu',
            'ν':'nu','ξ':'xi','ο':'omicron','π':'pi','ρ':'rho','σ':'sigma','ς':'sigma',
            'τ':'tau','υ':'upsilon','φ':'phi','χ':'chi','ψ':'psi','ω':'omega'
        };
        const _MATH_NAME_ALIASES = [
            [/\balfa\b/g, 'alpha'], [/\btetha\b/g, 'theta'], [/\bteta\b/g, 'theta'],
            [/\blyamda\b/g, 'lambda']
        ];
        const _MATH_TRIG_ALIASES = [
            [/\bctg\b/g, 'cot'], [/\bcotan\b/g, 'cot'], [/\btg\b/g, 'tan'],
            [/\bsh\b/g, 'sinh'], [/\bch\b/g, 'cosh'], [/\bth\b/g, 'tanh'], [/\bcth\b/g, 'coth']
        ];
        const _MATH_DEGREE_WORDS = [
            /\bdeg\b/g, /\bdegree\b/g, /\bdegrees\b/g, /\bgradus\b/g, /\bgradusda\b/g
        ];
        function mathNormalize(text) {
            if (text == null) return '';
            let s = String(text);
            // 1. NFC + casefold (toLowerCase is JS's nearest equivalent — locale-safe
            //    for the ASCII / Cyrillic / Greek subset used in math answers).
            s = s.normalize ? s.normalize('NFC') : s;
            s = s.toLowerCase();
            // 2. Strip leading "lhs =" prefix so "sin B = 0,6" → "0,6".
            const eqIdx = s.lastIndexOf('=');
            if (eqIdx !== -1) s = s.slice(eqIdx + 1);
            // 3. Greek glyphs → English names.
            for (const [g, name] of Object.entries(_MATH_GREEK)) {
                if (s.indexOf(g) !== -1) s = s.split(g).join(name);
            }
            // 4. Unicode minus / dashes → ASCII minus.
            s = s.replace(/[−–—‒－]/g, '-');
            // 5. Uzbek/Russian transliterations of Greek names → English canonical.
            for (const [pat, repl] of _MATH_NAME_ALIASES) s = s.replace(pat, repl);
            // 6. Trig aliases.
            for (const [pat, repl] of _MATH_TRIG_ALIASES) s = s.replace(pat, repl);
            // 7. Degree markers + words.
            s = s.replace(/[°º˚]/g, '');
            for (const w of _MATH_DEGREE_WORDS) s = s.replace(w, '');
            // 8. Decimal comma between digits → dot.
            s = s.replace(/(\d),(\d)/g, '$1.$2');
            // 9. Strip ALL whitespace.
            s = s.replace(/\s+/g, '');
            // 10. Trailing punctuation that doesn't change math meaning.
            s = s.replace(/[.,;:!?]+$/, '');
            return s;
        }
        // Expose for tests + other call sites (memory-sprint, sentence-fill could
        // adopt the same canonical form in future scoped fixes).
        window.mathNormalize = mathNormalize;

        async function gbAQAIGrade(question, studentAnswer, acceptList) {
            // Route Adaptive Quiz answers through the AI grader for language
            // subjects so different sentence forms / paraphrases are accepted
            // (e.g. "She has to do homework." ≡ "Doing homework is required of her.").
            // Closed verdict only — no AMR axes for AQ.
            try {
                const resp = await fetch('/api/ai/check-answer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question_id: 'aq-' + ((gbState.aq && gbState.aq.shown != null) ? (gbState.aq.shown + 1) : '?'),
                        question: question || '',
                        student_answer: studentAnswer,
                        expected_answers: acceptList,
                        answer_spec: {
                            type: 'semantic',
                            expected: (acceptList[0] || ''),
                            canonical_display: (acceptList[0] || ''),
                            allow_ai_fallback: true,
                            amr: false
                        },
                        allow_ai_fallback: true,
                        subject: (window.NETS_CTX && NETS_CTX.subject) || 'english',
                        grade: (window.NETS_CTX && NETS_CTX.grade) || 8,
                        tier: 'EASY',
                        phase: 'adaptive-quiz'
                    })
                });
                if (!resp.ok) return { correct: false, error: 'http ' + resp.status };
                return await resp.json();
            } catch (e) {
                return { correct: false, error: String(e) };
            }
        }

        async function gbAQAction() {
            const aq = gbState.aq;
            if (aq.answered) {
                // User clicked Next before the auto-advance timer fired — cancel
                // it to prevent double-advance.
                if (aq._autoAdvanceTimer) { clearTimeout(aq._autoAdvanceTimer); aq._autoAdvanceTimer = null; }
                aq.shown++; gbAQShowNext(); return;
            }
            // Bug AQ-2 fix: sync gate against fast double-clicks while the
            // language-subject AI grader is awaiting. Without this gate a
            // second click would re-enter gbAQAction (aq.answered is still
            // false because it's only set after the await), fire a second
            // gbAQAIGrade(...) request, and double-count the attempt.
            if (aq.busy) return;
            if (!aq.captureOk) {
                // Surface the missing-upload requirement on the status pill (no
                // capStatus element anymore). Toast also fires for redundancy.
                const sp = document.getElementById('aq-status-pill');
                if (sp) {
                    const prev = sp.textContent;
                    sp.classList.add('is-wrong');
                    sp.textContent = RT('aq.upload_first');
                    setTimeout(() => {
                        sp.classList.remove('is-wrong');
                        sp.textContent = prev || RT('aq.status_step1');
                    }, 1500);
                }
                gbAQToast(RT('aq.upload_first'));
                const gate = document.getElementById('aq-upload-gate');
                if (gate) gate.classList.add('show');
                return;
            }
            const inp = document.getElementById('gb-aq-textarea');
            const userVal = inp ? inp.value.trim() : '';
            if (!userVal) { if (inp) { inp.style.borderColor = '#d9534f'; setTimeout(() => { inp.style.borderColor = ''; }, 1200); } return; }
            const item = aq.currentItem;
            // AC-01: dual-pass match — first the legacy whitespace-stripped lowercase
            // compare (preserves prior behavior for English/non-math-text answers),
            // then a math-equivalence compare via mathNormalize (handles α/alfa/alpha,
            // tg/tan, ctg/cot, U+2212/-, decimal comma/dot, "lhs = rhs" prefix,
            // degree markers).
            const normLegacy = s => String(s == null ? '' : s).toLowerCase().replace(/\s+/g,'').trim();
            // Wave 2 fix (multi-answer): prefer item.acceptable[] (array of accepted answers).
            // Fall back to item.ans_all (legacy) and finally to item.answer (single string)
            // so old fixtures still work. Match is case-insensitive + whitespace-stripped.
            const acceptList = (Array.isArray(item.acceptable) && item.acceptable.length)
                ? item.acceptable
                : (Array.isArray(item.ans_all) && item.ans_all.length)
                    ? item.ans_all
                    : (item.answer != null ? [item.answer] : []);
            // Language subjects: route through the AI grader so paraphrases /
            // alternative sentence forms are accepted as right.
            // Other subjects: keep the deterministic string-match path (faster,
            // no token cost, deterministic for closed-form numeric answers).
            let isCorrect;
            if (gbIsLanguageSubject()) {
                // Bug AQ-2 fix: arm the busy gate + visually lock the action
                // button so a fast second click during the AI-grader await is
                // bounced at the early-return above. Cleared in the finally
                // block below (also runs on grader error) so the student can
                // retry if the network blips.
                aq.busy = true;
                if (inp) inp.disabled = true;
                if (btn) { btn.style.pointerEvents = 'none'; btn.classList.add('is-busy'); }
                try {
                    const result = await gbAQAIGrade(item.q || item.prompt || '', userVal, acceptList);
                    isCorrect = !!result.correct;
                } finally {
                    aq.busy = false;
                    if (btn) { btn.style.pointerEvents = ''; btn.classList.remove('is-busy'); }
                }
            } else {
                const userLegacy = normLegacy(userVal);
                const userMath = mathNormalize(userVal);
                isCorrect = acceptList.some(a => {
                    const aLegacy = normLegacy(a);
                    if (!aLegacy) return false;
                    if (aLegacy === userLegacy) return true;
                    // AC-01: math-equivalence pass. Two strings are equivalent if
                    // their canonical math form matches.
                    if (userMath && mathNormalize(a) === userMath) return true;
                    // Loose include for partial-form answers (matches legacy behavior).
                    return aLegacy.includes(userLegacy.split(/[,\s]/)[0]) || userLegacy.includes(aLegacy);
                });
            }
            aq.answered = true;
            if (inp) inp.disabled = true;
            const rb = document.getElementById('aq-result-box');
            const rTitle = document.getElementById('aq-result-title');
            const rText = document.getElementById('aq-result-text');
            const sp = document.getElementById('aq-status-pill');
            const displayAnswer = acceptList.length ? acceptList[0] : (item.answer || '');
            // item.work holds the author's hint/explanation. Only append it when
            // non-empty — otherwise we'd print just a trailing ". " or duplicate
            // the answer (when the injector used to default work to "Javob: X").
            const workSuffix = item.work ? ('. ' + item.work) : '';
            if (isCorrect) {
                aq.correct++;
                // Result box: green tint (no .wrong class). Title + body split — same
                // copy contract as the legacy single-string feedback (correct prefix
                // + work). Wrong-feedback path remains the only place the correct
                // answer appears in the DOM (no answer-leak before submit).
                if (rb) { rb.classList.remove('wrong'); rb.classList.add('show'); }
                if (rTitle) rTitle.textContent = RT('aq.correct_prefix').replace(/[!.\s]+$/, '');
                if (rText)  rText.textContent  = (item.work || '');
                if (sp) { sp.classList.remove('is-wrong'); sp.classList.add('is-correct'); sp.textContent = RT('aq.status_correct'); }
                if (item.tier === 'easy') aq.currentTier = 'medium';
                else if (item.tier === 'medium') aq.currentTier = 'hard';
            } else {
                if (rb) { rb.classList.add('wrong', 'show'); }
                if (rTitle) rTitle.textContent = RT('aq.wrong_prefix').replace(/[:.\s]+$/, '');
                if (rText)  rText.textContent  = displayAnswer + workSuffix;
                if (sp) { sp.classList.remove('is-correct'); sp.classList.add('is-wrong'); sp.textContent = RT('aq.status_review'); }
                if (item.tier === 'hard') aq.currentTier = 'medium';
                else if (item.tier === 'medium') aq.currentTier = 'easy';
            }
            // Log AQ result for the end-of-session AMR scorecard.
            // AQ items are closed-form numeric, so no AMR axes — score-only.
            if (window.__sessionLog) {
                window.__sessionLog.push({
                    phase: 'adaptive-quiz',
                    id: item.id || ('aq-' + (aq.shown + 1)),
                    tier: item.tier,
                    correct: isCorrect,
                    score: isCorrect ? 1 : 0,
                });
            }
            // Auto-advance: students don't need to click Next themselves. Show the
            // feedback for ~1.5s on correct, ~2.5s on wrong (so they can read the
            // correct answer + explanation), then move on. The button still works
            // as a manual skip — clicking it cancels the timer (see gbAQAction
            // entry guard).
            gbSetButtonNext(RT('btn.next_question'));
            if (aq._autoAdvanceTimer) clearTimeout(aq._autoAdvanceTimer);
            aq._autoAdvanceTimer = setTimeout(() => {
                aq._autoAdvanceTimer = null;
                if (!aq.answered) return; // safety: state already advanced elsewhere
                aq.shown++;
                gbAQShowNext();
            }, 2000);
        }

        function gbAQFinish() {
            // Registry-driven: skip empty games, exit Stage 5 if AQ was the only one.
            gbAdvanceFromGame(0, 'gb-panel-aq');
        }

        function gbInitWC() {
            gbState.wc = { chainIdx:0, levelIdx:0, retries:0 };
            gbWCRenderChain();
        }

        function gbWCRenderChain() {
            const wc = gbState.wc;
            const chain = GB_WHY_CHAIN[wc.chainIdx];
            const conv = document.getElementById('gb-wc-conv');
            if (conv) conv.innerHTML = '';
            const reprompt = document.getElementById('gb-wc-reprompt');
            if (reprompt) reprompt.className = 'gb-wc-reprompt';
            const invariant = document.getElementById('gb-wc-invariant');
            if (invariant) invariant.className = 'gb-wc-invariant';
            const ta = document.getElementById('gb-wc-textarea');
            if (ta) { ta.value = ''; ta.style.display = ''; ta.disabled = false; ta.style.borderColor = ''; }
            gbWCUpdateHeader();
            gbWCAppendProbe(chain.chain[0].probe);
            gbSetButtonForWC();
        }

        function gbWCUpdateHeader() {
            const wc = gbState.wc;
            for (let i = 1; i <= 3; i++) {
                const d = document.getElementById('gb-wcd-' + i);
                if (!d) continue;
                d.className = 'gb-wc-level-dot';
                if (i - 1 < wc.levelIdx) d.classList.add('done');
                else if (i - 1 === wc.levelIdx) d.classList.add('active');
            }
            const lbl = document.getElementById('gb-wc-chain-label');
            if (lbl) lbl.textContent = RT('wc.chain_label') + ' ' + (wc.chainIdx+1) + ' / 3 \u00b7 ' + RT('wc.level_label') + ' ' + (wc.levelIdx+1) + ' / 3';
        }

        function gbWCAppendProbe(text) {
            const conv = document.getElementById('gb-wc-conv');
            if (!conv) return;
            const b = document.createElement('div');
            b.className = 'gb-wc-bubble-ai';
            // innerHTML — sentence-fill prompt may contain inline images/SVGs/bold/italic.
            b.innerHTML = String(text == null ? '' : text);
            conv.appendChild(b);
            setTimeout(() => b.scrollIntoView({ behavior:'smooth', block:'nearest' }), 50);
        }

        function gbWCAppendStudentBubble(text) {
            const conv = document.getElementById('gb-wc-conv');
            if (!conv) return;
            const b = document.createElement('div');
            b.className = 'gb-wc-bubble-student';
            b.textContent = text;
            conv.appendChild(b);
            setTimeout(() => b.scrollIntoView({ behavior:'smooth', block:'nearest' }), 50);
        }

        // Sentence Fill is graded by /api/ai/check-answer with a text_fuzzy
        // answer_spec + AI fallback. The deterministic rapidfuzz checker
        // catches exact / minor-typo matches fast; for paraphrases and
        // synonyms, the Kimi semantic grader takes over (~1-3s).
        async function gbWCAIGrade(question, studentAnswer, expected) {
            try {
                const resp = await fetch('/api/ai/check-answer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question_id: 'wc-' + (gbState.wc.chainIdx + 1) + '-' + (gbState.wc.levelIdx + 1),
                        question: question || '',
                        student_answer: studentAnswer,
                        expected_answers: [expected],
                        // Sentence-fill answers are short and frequently
                        // expressed as synonyms or grammatical variants
                        // (e.g., "ayirmasi" ↔ "ayirmasining", "kichraytirish"
                        // ↔ "ayirish"). text_fuzzy bails below ratio 75
                        // without escalating, so we go straight to semantic
                        // — the deterministic checker always returns
                        // "unsure" and the AI does the meaning-aware match.
                        // Per GRADING.md: Sentence Fill (Phase 3) is CLOSED
                        // accuracy — no AMR axes. We only need a meaning-aware
                        // correct/wrong decision. amr is intentionally false.
                        answer_spec: {
                            type: 'semantic',
                            expected: expected,
                            canonical_display: expected,
                            allow_ai_fallback: true,
                            amr: false
                        },
                        allow_ai_fallback: true,
                        subject: (window.NETS_CTX && NETS_CTX.subject) || 'geometriya-g7-11',
                        grade: (window.NETS_CTX && NETS_CTX.grade) || 8,
                        tier: 'EASY',
                        phase: 'sentence-fill'
                    })
                });
                if (!resp.ok) return { correct: false, error: 'http ' + resp.status };
                return await resp.json();
            } catch (e) {
                return { correct: false, error: String(e) };
            }
        }

        async function gbWCAction() {
            const wc = gbState.wc;
            const ta = document.getElementById('gb-wc-textarea');
            const answer = ta ? ta.value.trim() : '';
            if (!answer) { if (ta) { ta.style.borderColor = '#d9534f'; setTimeout(() => { ta.style.borderColor = ''; }, 1200); } return; }
            const chain = GB_WHY_CHAIN[wc.chainIdx];
            const level = chain.chain[wc.levelIdx];
            gbWCAppendStudentBubble(answer);
            if (ta) { ta.value = ''; ta.disabled = true; }
            const reprompt = document.getElementById('gb-wc-reprompt');
            // Show "checking" indicator while AI grades.
            const checkingBubble = document.createElement('div');
            checkingBubble.className = 'gb-wc-bubble-ai gb-wc-bubble-checking';
            checkingBubble.innerHTML = '<em>' + RT('wc.checking') + '</em>';
            const conv = document.getElementById('gb-wc-conv');
            if (conv) conv.appendChild(checkingBubble);
            const result = await gbWCAIGrade(level.probe, answer, level.expect);
            if (checkingBubble && checkingBubble.parentNode) checkingBubble.parentNode.removeChild(checkingBubble);
            if (ta) ta.disabled = false;
            const ok = !!result.correct;
            // Log the result for the end-of-session scorecard. We log ONCE
            // per chain (not per sub-level) so the report mirrors the five
            // sentence-fill prompts the student saw.
            //
            // Per GRADING.md: Phase 3 Sentence Fill is CLOSED ACCURACY — no
            // AMR axes. The 2-axis rubric only applies to Phase 4 Real-Life
            // and Phase 6 Final Boss. Logging axes here would inflate the
            // overall axis means with non-rubric data.
            if (window.__sessionLog && (ok || wc.retries >= 1)) {
                window.__sessionLog.push({
                    phase: 'sentence-fill',
                    id: 'wc-' + (wc.chainIdx + 1),
                    correct: ok,
                    score: typeof result.score === 'number' ? result.score : (ok ? 1 : 0),
                    first_try: ok && wc.retries === 0,
                    closed: true,
                    feedback: result.feedback || '',
                });
            }
            if (ok) {
                wc.retries = 0;
                if (reprompt) reprompt.className = 'gb-wc-reprompt';
                // Surface the AI's positive feedback if provided.
                if (result.feedback && result.source === 'ai') gbWCAppendProbe('✓ ' + result.feedback);
                // First-try correct OR any-try correct: skip remaining hint
                // levels in this chain and jump straight to the invariant
                // (which advances to the next sentence-fill prompt). The old
                // flow forced the student through 3 sub-levels even after a
                // correct first-try answer.
                gbWCShowInvariant(chain);
            } else {
                wc.retries++;
                // Surface the AI hint if any so the student knows what's missing.
                if (result.feedback && result.source === 'ai') gbWCAppendProbe(result.feedback);
                if (wc.retries >= 2) {
                    wc.retries = 0;
                    if (reprompt) reprompt.className = 'gb-wc-reprompt';
                    gbWCAppendProbe(RT('wc.right_answer') + level.expect);
                    // After 2 wrong tries, reveal the answer and advance to
                    // the next chain — same skip behavior as a correct
                    // answer, but with the answer surfaced first.
                    gbWCShowInvariant(chain);
                } else {
                    if (reprompt) reprompt.classList.add('show');
                    gbSetButtonForWC();
                }
            }
        }

        function gbWCShowInvariant(chain) {
            const inv = document.getElementById('gb-wc-invariant');
            const invText = document.getElementById('gb-wc-invariant-text');
            if (invText) invText.textContent = chain.invariant;
            if (inv) inv.classList.add('show');
            const ta = document.getElementById('gb-wc-textarea');
            if (ta) ta.style.display = 'none';
            gbSetButtonNext(gbState.wc.chainIdx < GB_WHY_CHAIN.length - 1 ? RT('btn.next_chain') : (gbIsLastGame(1) ? RT('btn.next_stage') : RT('btn.next_game')));
        }

        function gbWCNextChain() {
            const wc = gbState.wc;
            if (wc.chainIdx < GB_WHY_CHAIN.length - 1) {
                wc.chainIdx++; wc.levelIdx = 0; wc.retries = 0;
                gbWCRenderChain();
            } else gbWCFinish();
        }

        function gbWCFinish() {
            // Registry-driven: walk to next active game, or exit Stage 5.
            gbAdvanceFromGame(1, 'gb-panel-wc');
        }

        // ── Sentence Fill (Stage-5 sub-game 6) ──────────────────────────
        // Cloze-style fill-in-the-blank with two modes: word_bank (pick chips)
        // and free_recall (type into inputs). Each blank is graded independently
        // via /api/ai/check-answer with phase='sentence-fill'. After 2 wrong
        // attempts, the blank locks and the correct answer is revealed only via
        // result.correct_answer from the backend (never embedded in client data).
        let _gbSFListenersBound = false;
        let _gbSFToastTimer = null;

        function gbSetButtonForSF() {
            btn.classList.remove('pulse','state-pill','state-line');
            btn.classList.add('state-pill');
            setBtnText(RT('sf.btn_check'));
            btn.classList.add('pulse');
        }

        async function gbSFGradeBlank(itemId, blankIdx, studentValue, attemptNumber) {
            try {
                const ctx = window.NETS_CTX || {};
                const resp = await fetch('/api/ai/check-answer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        phase: 'sentence-fill',
                        // NETS_CTX exposes `hwId` per server/routes/homework_page.py
                        // runtime_ctx; probe homework_id / homeworkId for forward-compat.
                        // Mirrors gbTMCheckPair's lookup chain (PR #140).
                        homework_id: ctx.hwId || ctx.homework_id || ctx.homeworkId || null,
                        question_id: itemId,
                        student_answer: studentValue,
                        // Forward-compat fields:
                        blank_idx: blankIdx,
                        attempt_number: attemptNumber,
                        item_id: itemId,
                        student_value: studentValue,
                        subject: ctx.subject || 'general',
                        grade: ctx.grade || 8,
                        expected_answers: [],
                        answer_spec: {
                            type: 'semantic',
                            expected: '',
                            canonical_display: '',
                            allow_ai_fallback: true,
                            amr: false
                        },
                        allow_ai_fallback: true
                    })
                });
                if (!resp.ok) {
                    return {
                        correct: false,
                        lock: attemptNumber >= 2,
                        correct_answer: null,
                        explanation: null,
                        xp: { base: 0, first_attempt_bonus: 0, total: 0 },
                        error: 'http ' + resp.status
                    };
                }
                const data = await resp.json();
                const isCorrect = !!(data.is_correct === true || data.correct === true);
                const lock = isCorrect || attemptNumber >= 2;
                const revealedAnswer = (!isCorrect && attemptNumber >= 2)
                    ? (data.expected || data.canonical_display || data.correct_answer || null)
                    : null;
                return {
                    correct: isCorrect,
                    lock: lock,
                    correct_answer: revealedAnswer,
                    explanation: data.explanation || null,
                    xp: {
                        base: isCorrect ? 100 : 0,
                        first_attempt_bonus: (isCorrect && attemptNumber === 1) ? 25 : 0,
                        total: isCorrect ? (attemptNumber === 1 ? 125 : 100) : 0
                    }
                };
            } catch (e) {
                return {
                    correct: false,
                    lock: attemptNumber >= 2,
                    correct_answer: null,
                    explanation: null,
                    xp: { base: 0, first_attempt_bonus: 0, total: 0 },
                    error: String(e)
                };
            }
        }

        function gbInitSF() {
            // Reset state for slot 6.
            gbState.sf = { idx:0, mode:(gbState.sf && gbState.sf.mode) || 'word_bank', selectedBlank:0, blanks:[], xp:0, pendingFinalize:false, complete:false, busy:false };
            // Eyebrow + chain label + dots (one per item).
            const eyebrow = document.getElementById('gb-sf-eyebrow');
            if (eyebrow) eyebrow.textContent = (RT('sf.eyebrow') || '').toUpperCase();
            const dots = document.getElementById('gb-sf-dots');
            if (dots) {
                dots.innerHTML = '';
                const total = Array.isArray(GB_SENTENCE_FILL) ? GB_SENTENCE_FILL.length : 0;
                for (let i = 0; i < total; i++) {
                    const d = document.createElement('span');
                    if (i === 0) d.classList.add('active');
                    dots.appendChild(d);
                }
            }
            const progressLabel = document.getElementById('gb-sf-progress-label');
            if (progressLabel) {
                const total = Array.isArray(GB_SENTENCE_FILL) ? GB_SENTENCE_FILL.length : 0;
                progressLabel.textContent = (gbState.sf.idx + 1) + '/' + total + ' ' + RT('sf.title');
            }
            const chainLabel = document.getElementById('gb-sf-chain-label');
            if (chainLabel) {
                const total = Array.isArray(GB_SENTENCE_FILL) ? GB_SENTENCE_FILL.length : 0;
                chainLabel.textContent = RT('sf.chain_label') + ' ' + (gbState.sf.idx + 1) + '/' + total;
            }
            // Keyboard listener — bind once. Mode is author-set in the
            // builder per content_json item; there is no runtime mode toggle.
            if (!_gbSFListenersBound) {
                document.addEventListener('keydown', (e) => {
                    if (gbState.subGame !== 6) return;
                    const sfPanel = document.getElementById('gb-panel-sf');
                    if (!sfPanel || !sfPanel.classList.contains('active')) return;
                    if (gbState.sf.complete || gbState.sf.busy) return;
                    const focused = document.activeElement;
                    const isInput = focused && focused.classList && focused.classList.contains('gb-sf-recall-input');
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        gbSFAction();
                        return;
                    }
                    if (e.key === 'Backspace' && !isInput) {
                        const idx = gbState.sf.selectedBlank;
                        const blank = gbState.sf.blanks[idx];
                        if (blank && !blank.locked && blank.value) {
                            e.preventDefault();
                            blank.value = '';
                            const blankEl = document.querySelector('.gb-sf-blank[data-index="' + idx + '"]');
                            if (blankEl) {
                                blankEl.removeAttribute('data-value');
                                blankEl.textContent = '';
                                blankEl.classList.add('empty');
                            }
                            gbSFSyncUsedWords();
                        }
                    }
                });
                _gbSFListenersBound = true;
            }
            // Hide result card from any prior render.
            const resultCard = document.getElementById('gb-sf-result-card');
            if (resultCard) resultCard.classList.remove('show');
            gbSFRenderItem();
        }

        function gbSFRenderItem() {
            const items = Array.isArray(GB_SENTENCE_FILL) ? GB_SENTENCE_FILL : [];
            const item = items[gbState.sf.idx];
            if (!item) { gbSFFinish(); return; }
            // Default mode if missing on item.
            const mode = item.mode || gbState.sf.mode || 'word_bank';
            // Init blanks array based on '___' count.
            const blankCount = (item.passage || '').split('___').length - 1;
            gbState.sf.blanks = [];
            for (let i = 0; i < blankCount; i++) {
                gbState.sf.blanks.push({ value:'', attempts:0, locked:false, correct:false, revealed:null });
            }
            gbState.sf.selectedBlank = 0;
            // Reset XP pill + score line.
            const xpPill = document.getElementById('gb-sf-xp-pill');
            if (xpPill) xpPill.textContent = '0 XP';
            const scoreLabel = document.getElementById('gb-sf-score-label');
            if (scoreLabel) scoreLabel.textContent = RT('sf.score_label');
            const scoreValue = document.getElementById('gb-sf-score-value');
            if (scoreValue) scoreValue.textContent = '0 XP';
            // Title + meta.
            const titleEl = document.getElementById('gb-sf-title');
            if (titleEl) titleEl.textContent = RT('sf.title');
            const metaEl = document.getElementById('gb-sf-eyebrow-meta');
            if (metaEl) metaEl.textContent = item.tags || '';
            // Update progress dots + label.
            const dots = document.getElementById('gb-sf-dots');
            if (dots) {
                const spans = dots.querySelectorAll('span');
                spans.forEach((s, i) => { s.classList.toggle('active', i === gbState.sf.idx); });
            }
            const progressLabel = document.getElementById('gb-sf-progress-label');
            if (progressLabel) progressLabel.textContent = (gbState.sf.idx + 1) + '/' + items.length + ' ' + RT('sf.title');
            const chainLabel = document.getElementById('gb-sf-chain-label');
            if (chainLabel) chainLabel.textContent = RT('sf.chain_label') + ' ' + (gbState.sf.idx + 1) + '/' + items.length;
            // Hide result card.
            const resultCard = document.getElementById('gb-sf-result-card');
            if (resultCard) resultCard.classList.remove('show');
            // Render passage + apply mode + select first blank.
            gbSFRenderPassage(item);
            gbSFApplyMode(mode);
            gbSFSelectBlank(0);
            // Reset action button.
            setBtnText(RT('sf.btn_check'));
        }

        function gbSFRenderPassage(item) {
            const cloze = document.getElementById('gb-sf-cloze-text');
            if (!cloze) return;
            cloze.innerHTML = '';
            const passage = item.passage || '';
            const segments = passage.split('___');
            const blankIcons = Array.isArray(item.blank_icons) ? item.blank_icons : [];
            const colorHints = (item.color_hints && typeof item.color_hints === 'object') ? item.color_hints : {};
            const iconMap = { lightbulb: '💡', star: '⭐' };
            const escapeRe = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const appendTextSeg = (text) => {
                if (!text) return;
                let html = text;
                try {
                    const words = Object.keys(colorHints);
                    if (words.length) {
                        html = html.replace(/[<>&]/g, (c) => ({ '<':'&lt;', '>':'&gt;', '&':'&amp;' }[c]));
                        words.forEach((w) => {
                            if (!w) return;
                            const re = new RegExp('\\b(' + escapeRe(w) + ')\\b', 'g');
                            html = html.replace(re, '<span class="gb-sf-color-hint" style="color: var(--accent)">$1</span>');
                        });
                        const span = document.createElement('span');
                        span.innerHTML = html;
                        cloze.appendChild(span);
                        return;
                    }
                } catch (_) { /* fall through to plain text */ }
                cloze.appendChild(document.createTextNode(text));
            };
            for (let i = 0; i < segments.length; i++) {
                appendTextSeg(segments[i]);
                if (i < segments.length - 1) {
                    const blankBtn = document.createElement('button');
                    blankBtn.type = 'button';
                    blankBtn.className = 'gb-sf-blank empty';
                    blankBtn.setAttribute('data-index', String(i));
                    blankBtn.setAttribute('data-number', String(i + 1));
                    const iconKey = blankIcons[i];
                    const iconChar = iconKey && iconMap[iconKey] ? iconMap[iconKey] + ' ' : '';
                    if (iconChar) blankBtn.textContent = iconChar;
                    const idxLocal = i;
                    blankBtn.addEventListener('click', () => gbSFSelectBlank(idxLocal));
                    cloze.appendChild(blankBtn);
                }
            }
            const passageLabel = document.getElementById('gb-sf-passage-label');
            if (passageLabel) {
                passageLabel.textContent = RT('sf.passage_label') + (item.tags ? ' · ' + item.tags : '');
            }
        }

        function gbSFApplyMode(mode) {
            // Mode is author-set per item in the builder (content_json).
            // Runtime renders the chosen mode only — no student toggle.
            gbState.sf.mode = mode;
            const chip = document.getElementById('gb-sf-mode-chip');
            if (chip) {
                chip.textContent = mode === 'word_bank' ? RT('sf.mode_word_bank') : RT('sf.mode_free_recall');
                chip.setAttribute('data-mode', mode);
            }
            const microcopy = document.getElementById('gb-sf-microcopy');
            if (microcopy) {
                microcopy.textContent = mode === 'word_bank' ? RT('sf.subtitle_bank') : RT('sf.subtitle_recall');
            }
            const subtitle = document.getElementById('gb-sf-subtitle');
            if (subtitle) {
                subtitle.textContent = mode === 'word_bank' ? RT('sf.subtitle_bank') : RT('sf.subtitle_recall');
            }
            const wordBank = document.getElementById('gb-sf-word-bank');
            const recallGrid = document.getElementById('gb-sf-recall-grid');
            const items = Array.isArray(GB_SENTENCE_FILL) ? GB_SENTENCE_FILL : [];
            const item = items[gbState.sf.idx] || {};
            if (mode === 'word_bank') {
                if (wordBank) {
                    wordBank.style.display = 'flex';
                    wordBank.innerHTML = '';
                    const bank = Array.isArray(item.word_bank) ? item.word_bank : [];
                    bank.forEach((word) => {
                        const chip = document.createElement('button');
                        chip.type = 'button';
                        chip.className = 'gb-sf-word';
                        chip.setAttribute('data-word', String(word));
                        chip.textContent = String(word);
                        chip.addEventListener('click', () => gbSFPickWord(String(word)));
                        wordBank.appendChild(chip);
                    });
                }
                if (recallGrid) {
                    recallGrid.classList.remove('show');
                    recallGrid.innerHTML = '';
                }
                gbSFSyncUsedWords();
            } else {
                if (wordBank) {
                    wordBank.style.display = 'none';
                }
                if (recallGrid) {
                    recallGrid.classList.add('show');
                    recallGrid.innerHTML = '';
                    gbState.sf.blanks.forEach((blank, idx) => {
                        const input = document.createElement('input');
                        input.type = 'text';
                        input.className = 'gb-sf-recall-input';
                        input.id = 'gb-sf-recall-' + idx;
                        input.setAttribute('data-index', String(idx));
                        input.setAttribute('autocomplete', 'off');
                        input.placeholder = 'Blank ' + (idx + 1);
                        input.value = blank.value || '';
                        if (blank.locked) input.disabled = true;
                        input.addEventListener('input', (e) => {
                            const i = parseInt(e.target.getAttribute('data-index'), 10);
                            if (gbState.sf.blanks[i] && !gbState.sf.blanks[i].locked) {
                                gbState.sf.blanks[i].value = e.target.value;
                                // Reflect into the cloze blank as well so sync visuals stay coherent.
                                const blankEl = document.querySelector('.gb-sf-blank[data-index="' + i + '"]');
                                if (blankEl) {
                                    if (e.target.value) {
                                        blankEl.setAttribute('data-value', e.target.value);
                                        blankEl.textContent = e.target.value;
                                        blankEl.classList.remove('empty');
                                    } else {
                                        blankEl.removeAttribute('data-value');
                                        blankEl.textContent = '';
                                        blankEl.classList.add('empty');
                                    }
                                }
                            }
                        });
                        recallGrid.appendChild(input);
                    });
                }
            }
            const kbHint = document.getElementById('gb-sf-keyboard-hint');
            if (kbHint) kbHint.textContent = RT('sf.keyboard_hint');
        }

        function gbSFSelectBlank(idx) {
            const blanks = gbState.sf.blanks || [];
            if (!blanks.length) return;
            // If target blank is locked, advance to first non-locked.
            let target = idx;
            if (blanks[target] && blanks[target].locked) {
                let scan = -1;
                for (let i = 0; i < blanks.length; i++) {
                    if (!blanks[i].locked) { scan = i; break; }
                }
                if (scan === -1) return;
                target = scan;
            }
            gbState.sf.selectedBlank = target;
            const all = document.querySelectorAll('.gb-sf-blank');
            all.forEach((el) => {
                const i = parseInt(el.getAttribute('data-index'), 10);
                const isLocked = blanks[i] && blanks[i].locked;
                if (!isLocked) el.classList.toggle('active', i === target);
                else el.classList.remove('active');
            });
        }

        function gbSFPickWord(word) {
            if (gbState.sf.mode !== 'word_bank') return;
            const idx = gbState.sf.selectedBlank;
            const blank = gbState.sf.blanks[idx];
            if (!blank || blank.locked) return;
            blank.value = word;
            const blankEl = document.querySelector('.gb-sf-blank[data-index="' + idx + '"]');
            if (blankEl) {
                blankEl.setAttribute('data-value', word);
                blankEl.textContent = word;
                blankEl.classList.remove('empty');
            }
            gbSFSyncUsedWords();
            // Auto-advance to next non-locked, non-filled blank.
            const blanks = gbState.sf.blanks;
            for (let step = 1; step <= blanks.length; step++) {
                const nxt = (idx + step) % blanks.length;
                const b = blanks[nxt];
                if (b && !b.locked && !b.value) {
                    gbSFSelectBlank(nxt);
                    return;
                }
            }
        }

        function gbSFSyncUsedWords() {
            const used = new Set();
            (gbState.sf.blanks || []).forEach((b) => {
                if (b && b.value) used.add(String(b.value));
            });
            const chips = document.querySelectorAll('.gb-sf-word');
            chips.forEach((chip) => {
                const w = chip.getAttribute('data-word');
                chip.classList.toggle('used', used.has(w));
            });
        }

        async function gbSFAction() {
            if (gbState.sf.busy) return;
            const items = Array.isArray(GB_SENTENCE_FILL) ? GB_SENTENCE_FILL : [];
            const item = items[gbState.sf.idx];
            if (!item) { gbSFFinish(); return; }
            const resultCard = document.getElementById('gb-sf-result-card');
            // If result card is showing, this click means "next".
            if (resultCard && resultCard.classList.contains('show')) {
                if (gbState.sf.idx < items.length - 1) {
                    gbState.sf.idx += 1;
                    gbSFRenderItem();
                    setBtnText(RT('sf.btn_check'));
                } else {
                    gbSFFinish();
                }
                return;
            }
            // Free-recall mode: pull current values from inputs (defensive sync).
            if (gbState.sf.mode === 'free_recall') {
                (gbState.sf.blanks || []).forEach((b, i) => {
                    if (!b.locked) {
                        const input = document.getElementById('gb-sf-recall-' + i);
                        if (input) b.value = (input.value || '').trim();
                    }
                });
            }
            // Validate: every non-locked blank must have a value.
            const missing = (gbState.sf.blanks || []).some((b) => !b.locked && !String(b.value || '').trim());
            if (missing) {
                gbSFShowToast(RT('sf.subtitle_recall'));
                return;
            }
            gbState.sf.busy = true;
            let totalXp = 0;
            const blanks = gbState.sf.blanks;
            for (let i = 0; i < blanks.length; i++) {
                const b = blanks[i];
                if (b.locked) continue;
                const attemptNumber = b.attempts + 1;
                const result = await gbSFGradeBlank(item.id, i, b.value, attemptNumber);
                b.attempts = attemptNumber;
                const blankEl = document.querySelector('.gb-sf-blank[data-index="' + i + '"]');
                if (result.correct) {
                    b.correct = true;
                    b.locked = true;
                    if (blankEl) {
                        blankEl.classList.remove('wrong','active','empty');
                        blankEl.classList.add('correct','locked');
                    }
                } else {
                    if (blankEl) {
                        blankEl.classList.remove('correct','active');
                        blankEl.classList.add('wrong');
                    }
                    if (result.lock) {
                        b.locked = true;
                        if (result.correct_answer) {
                            b.revealed = result.correct_answer;
                            b.value = result.correct_answer;
                            if (blankEl) {
                                blankEl.setAttribute('data-value', result.correct_answer);
                                blankEl.textContent = result.correct_answer;
                                blankEl.classList.remove('empty','wrong');
                                blankEl.classList.add('locked');
                            }
                            // Reflect reveal into recall input if shown.
                            const input = document.getElementById('gb-sf-recall-' + i);
                            if (input) { input.value = result.correct_answer; input.disabled = true; }
                        }
                    }
                }
                totalXp += (result.xp && typeof result.xp.total === 'number') ? result.xp.total : 0;
            }
            // Compute perfect fill: all correct AND every attempts === 1.
            const perfect = blanks.every((b) => b.correct === true && b.attempts === 1);
            if (perfect) totalXp += 100;
            gbState.sf.xp = totalXp;
            // Update XP pill + score line.
            const xpPill = document.getElementById('gb-sf-xp-pill');
            if (xpPill) xpPill.textContent = totalXp + ' XP';
            const scoreValue = document.getElementById('gb-sf-score-value');
            if (scoreValue) scoreValue.textContent = totalXp + ' XP';
            // Toast + result card.
            gbSFShowToast(perfect ? RT('sf.toast_perfect') : RT('sf.toast_partial'));
            const resultTitle = document.getElementById('gb-sf-result-title');
            const resultText = document.getElementById('gb-sf-result-text');
            if (resultTitle) resultTitle.textContent = perfect ? RT('sf.result_perfect') : RT('sf.result_partial');
            if (resultText) resultText.textContent = perfect ? RT('sf.perfect_fill_bonus') : RT('sf.first_attempt_bonus');
            if (resultCard) resultCard.classList.add('show');
            // Set button to Next.
            setBtnText(RT('sf.btn_next'));
            // Session log.
            if (window.__sessionLog) {
                const correctCount = blanks.filter((b) => b.correct).length;
                window.__sessionLog.push({
                    phase: 'sentence-fill',
                    id: item.id || ('sf-' + (gbState.sf.idx + 1)),
                    correct: correctCount === blanks.length,
                    score: blanks.length ? (correctCount / blanks.length) : 0,
                    first_try: perfect,
                    closed: true,
                    xp: totalXp
                });
            }
            gbState.sf.busy = false;
        }

        function gbSFShowToast(text) {
            const toast = document.getElementById('gb-sf-toast');
            if (!toast) return;
            toast.textContent = text || '';
            toast.classList.add('show');
            if (_gbSFToastTimer) clearTimeout(_gbSFToastTimer);
            _gbSFToastTimer = setTimeout(() => {
                toast.classList.remove('show');
                _gbSFToastTimer = null;
            }, 2000);
        }

        function gbSFFinish() {
            gbState.sf.complete = true;
            gbAdvanceFromGame(6, 'gb-panel-sf');
        }

        // Tile Match — left/right column matching.
        // Left column shows all `a` sides in order; right column shows all
        // `b` sides shuffled. Click a left tile, then click a right tile to
        // attempt a match. Match → both lock green. Wrong → red flash, both
        // deselect. Win at GB_MEMORY_MATCH.length matched.
        function gbInitMM() {
            const mm = gbState.mm;
            const total = GB_MEMORY_MATCH.length;
            // Left side keeps source order; right side is shuffled.
            const lefts  = GB_MEMORY_MATCH.map((p, i) => ({ pairId: i, text: p.a }));
            const rights = GB_MEMORY_MATCH.map((p, i) => ({ pairId: i, text: p.b }));
            for (let i = rights.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [rights[i], rights[j]] = [rights[j], rights[i]];
            }
            mm.lefts = lefts;
            mm.rights = rights;
            mm.matched = 0;
            mm.total = total;
            mm.selectedLeft = null;
            mm.busy = false;
            const win = document.getElementById('gb-mm-win-banner');
            if (win) win.className = 'gb-mm-win-banner';
            gbMMRenderBoard();
            gbMMUpdateStatus();
        }

        function gbMMRenderBoard() {
            const left  = document.getElementById('gb-tm-left');
            const right = document.getElementById('gb-tm-right');
            if (!left || !right) return;
            left.innerHTML = '';
            right.innerHTML = '';
            gbState.mm.lefts.forEach((tile) => {
                const el = document.createElement('div');
                el.className = 'gb-tm-tile gb-tm-left-tile';
                el.dataset.pair = tile.pairId;
                el.dataset.side = 'left';
                el.innerHTML = tile.text;
                el.addEventListener('click', () => gbMMSelectLeft(tile.pairId, el));
                left.appendChild(el);
            });
            gbState.mm.rights.forEach((tile) => {
                const el = document.createElement('div');
                el.className = 'gb-tm-tile gb-tm-right-tile';
                el.dataset.pair = tile.pairId;
                el.dataset.side = 'right';
                el.innerHTML = tile.text;
                el.addEventListener('click', () => gbMMTryMatch(tile.pairId, el));
                right.appendChild(el);
            });
            // Re-render any KaTeX/math the board contains (the tiles are
            // populated after the page-level KaTeX pass ran).
            if (typeof window.__renderMath === 'function') window.__renderMath();
        }

        function gbMMUpdateStatus() {
            const st = document.getElementById('gb-mm-status');
            if (st) st.textContent = RT('tm.pairs_status') + ' ' + gbState.mm.matched + ' / ' + (gbState.mm.total || GB_MEMORY_MATCH.length);
        }

        function gbMMSelectLeft(pairId, el) {
            const mm = gbState.mm;
            if (mm.busy) return;
            if (el.classList.contains('matched')) return;
            // Clear any prior left selection
            document.querySelectorAll('.gb-tm-left-tile.selected').forEach(n => n.classList.remove('selected'));
            // Toggle off if same tile clicked twice
            if (mm.selectedLeft && mm.selectedLeft.pairId === pairId) {
                mm.selectedLeft = null;
                return;
            }
            el.classList.add('selected');
            mm.selectedLeft = { pairId, el };
        }

        function gbMMTryMatch(rightPairId, rightEl) {
            const mm = gbState.mm;
            if (mm.busy) return;
            if (rightEl.classList.contains('matched')) return;
            if (!mm.selectedLeft) {
                // No left tile selected — flash the right tile to hint at order.
                rightEl.classList.add('wrong-flash');
                setTimeout(() => rightEl.classList.remove('wrong-flash'), 360);
                return;
            }
            const leftEl = mm.selectedLeft.el;
            const matches = mm.selectedLeft.pairId === rightPairId;
            if (matches) {
                leftEl.classList.remove('selected');
                leftEl.classList.add('matched');
                rightEl.classList.add('matched');
                mm.matched++;
                mm.selectedLeft = null;
                gbMMUpdateStatus();
                if (mm.matched >= mm.total) gbMMWin();
            } else {
                mm.busy = true;
                leftEl.classList.add('wrong-flash');
                rightEl.classList.add('wrong-flash');
                setTimeout(() => {
                    leftEl.classList.remove('wrong-flash');
                    rightEl.classList.remove('wrong-flash');
                    leftEl.classList.remove('selected');
                    mm.selectedLeft = null;
                    mm.busy = false;
                }, 420);
            }
        }

        // No-op shim — the runtime button handler used to call gbMMAction()
        // for the legacy confirm-question mechanic. Tile Match is fully
        // self-driven via tile clicks, so the action button stays inert.
        function gbMMAction() { /* intentionally empty */ }

        function gbMMWin() {
            const win = document.getElementById('gb-mm-win-banner');
            if (win) win.classList.add('show');
            gbState.mm.complete = true;
            // Log Tile Match phase outcome — pure self-grade, all 6 pairs
            // matched = 100% for the AMR scorecard.
            if (window.__sessionLog) {
                window.__sessionLog.push({
                    phase: 'tile-match', id: 'tm-all',
                    correct: true, score: 1,
                });
            }
            // Registry decides next game on click; we just label the button.
            gbSetButtonNext(gbIsLastGame(2) ? RT('btn.next_stage') : RT('btn.next_game'));
        }

        // ── TILE MATCH (gbTM*, panel: gb-panel-tm) ──
        // Server-graded cloze-match. Single network swap-point: gbTMCheckPair.
        // Answer-leak guard: tiles only carry data-pair-id; hint text comes from
        // server response on wrong picks — never from a client-side lookup.
        function gbInitTM() {
            const tm = gbState.tm;
            tm.tiles = [];
            tm.pairsTotal = 0;
            tm.matched = 0;
            tm.wrong = 0;
            tm.streak = 0;
            tm.xp = 0;
            tm.selectedLeft = null;
            tm.busy = false;
            tm.complete = false;
            tm.startedAt = null;
            tm.outcome = null;
            tm._toastTimer = null;
            tm.sessionId = gbTMSessionId();

            const flat = Array.isArray(GB_TILE_MATCH) ? GB_TILE_MATCH : [];
            if (!flat.length) {
                console.warn('[gbInitTM] GB_TILE_MATCH is empty; hiding panel');
                const panel = document.getElementById('gb-panel-tm');
                if (panel) panel.style.display = 'none';
                return;
            }

            const lefts = flat.filter(function (e) { return e && e.side === 'left'; });
            const rights = flat.filter(function (e) { return e && e.side === 'right'; });
            tm.pairsTotal = lefts.length;
            tm.tiles = flat.slice();

            const leftsShuffled = gbTMShuffle(lefts);
            const rightsShuffled = gbTMShuffle(rights);

            gbTMRenderStaticI18n();
            gbTMRenderBoard(leftsShuffled, rightsShuffled);
            gbTMUpdateStats();
            gbTMUpdateXp(0);

            const resultCard = document.getElementById('gb-tm-result-card');
            if (resultCard) resultCard.classList.remove('show');

            if (typeof gbSetButtonNext === 'function') {
                // Hide the action button during play — the dock label is
                // informational and the user advances by tapping tiles.
                gbSetButtonNext(RT('tm.dock_select'), /*hidden*/ true);
            }


            tm.startedAt = Date.now();
        }

        function gbTMRenderStaticI18n() {
            const setText = function (id, key) {
                const el = document.getElementById(id);
                if (el) el.textContent = RT(key);
            };
            setText('gb-tm-eyebrow', 'tm.eyebrow');
            setText('gb-tm-title', 'tm.title');
            setText('gb-tm-subtitle', 'tm.subtitle');
            setText('gb-tm-stat-matched-label', 'tm.stats_matched');
            setText('gb-tm-stat-wrong-label', 'tm.stats_wrong');
            setText('gb-tm-board-copy', 'tm.subtitle');
            setText('gb-tm-col-left-label', 'tm.col_left');
            setText('gb-tm-col-right-label', 'tm.col_right');
            setText('gb-tm-score-label', 'tm.xp_label');
        }

        function gbTMShuffle(arr) {
            const out = Array.isArray(arr) ? arr.slice() : [];
            for (let i = out.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                const tmp = out[i];
                out[i] = out[j];
                out[j] = tmp;
            }
            return out;
        }

        function gbTMSessionId() {
            if (window.crypto && typeof window.crypto.randomUUID === 'function') {
                try { return 'tm-' + window.crypto.randomUUID(); } catch (e) { /* fallback below */ }
            }
            return 'tm-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
        }

        function gbTMRenderBoard(lefts, rights) {
            const leftCol = document.getElementById('gb-tm-left');
            const rightCol = document.getElementById('gb-tm-right');
            if (!leftCol || !rightCol) return;
            leftCol.innerHTML = '';
            rightCol.innerHTML = '';

            lefts.forEach(function (entry) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'gb-tm-tile gb-tm-tile-left';
                btn.setAttribute('data-pair-id', entry.id);
                btn.innerHTML = entry.text != null ? String(entry.text) : '';
                btn.addEventListener('click', function () {
                    gbTMSelectLeft(entry.id, btn);
                });
                leftCol.appendChild(btn);
            });

            rights.forEach(function (entry) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'gb-tm-tile gb-tm-tile-right';
                btn.setAttribute('data-pair-id', entry.id);
                btn.innerHTML = entry.text != null ? String(entry.text) : '';
                btn.addEventListener('click', function () {
                    gbTMTryMatch(entry.id, btn);
                });
                rightCol.appendChild(btn);
            });

            if (typeof window.__renderMath === 'function') {
                try { window.__renderMath(); } catch (e) { /* non-fatal */ }
            }
        }

        function gbTMSelectLeft(pairId, el) {
            const tm = gbState.tm;
            if (!tm || tm.busy) return;
            if (!el || el.classList.contains('matched')) return;

            // Toggle off if same tile clicked twice.
            if (tm.selectedLeft && tm.selectedLeft.el === el) {
                el.classList.remove('selected');
                tm.selectedLeft = null;
                if (typeof gbSetButtonNext === 'function') {
                    gbSetButtonNext(RT('tm.dock_select'), /*hidden*/ true);
                }
                return;
            }

            // Clear any prior selection on the left column.
            const leftCol = document.getElementById('gb-tm-left');
            if (leftCol) {
                const prior = leftCol.querySelectorAll('.gb-tm-tile-left.selected');
                prior.forEach(function (p) { p.classList.remove('selected'); });
            }

            el.classList.add('selected');
            tm.selectedLeft = { id: pairId, el: el };
            if (typeof gbSetButtonNext === 'function') {
                gbSetButtonNext(RT('tm.dock_choose_meaning'), /*hidden*/ true);
            }
        }

        async function gbTMTryMatch(rightPairId, rightEl) {
            const tm = gbState.tm;
            if (!tm || tm.busy) return;
            if (!rightEl || rightEl.classList.contains('matched')) return;

            if (!tm.selectedLeft) {
                rightEl.classList.add('wrong');
                setTimeout(function () { rightEl.classList.remove('wrong'); }, 320);
                gbTMShowToast(RT('tm.toast_pick_left'), 'wrong');
                return;
            }

            tm.busy = true;
            const leftEl = tm.selectedLeft.el;
            const leftId = tm.selectedLeft.id;

            const resp = await gbTMCheckPair(leftId, rightPairId);
            gbTMHandleResponse(resp, leftEl, rightEl);
        }

        async function gbTMCheckPair(leftId, rightId) {
            const ctx = window.NETS_CTX || {};
            // NETS_CTX uses `hwId` per server/routes/homework_page.py runtime_ctx;
            // also probe homework_id / homeworkId for forward-compat.
            const homeworkId = ctx.hwId || ctx.homework_id || ctx.homeworkId || null;
            if (!homeworkId) {
                console.warn('[gbTMCheckPair] missing homework_id; skipping check');
                return null;
            }
            try {
                const res = await fetch('/api/ai/check-answer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        homework_id: homeworkId,
                        phase: 'tile-match',
                        session_id: (gbState.tm && gbState.tm.sessionId) || null,
                        left_id: leftId,
                        right_id: rightId,
                    }),
                });
                if (!res.ok) {
                    console.error('[gbTMCheckPair] HTTP ' + res.status);
                    return null;
                }
                return await res.json();
            } catch (err) {
                console.error('[gbTMCheckPair] network error', err);
                return null;
            }
        }

        function gbTMHandleResponse(resp, leftEl, rightEl) {
            const tm = gbState.tm;
            if (!resp) {
                // Network/HTTP failure: release lock, deselect, toast wrong.
                if (leftEl) leftEl.classList.remove('selected');
                tm.selectedLeft = null;
                tm.busy = false;
                gbTMShowToast(RT('tm.toast_wrong'), 'wrong');
                return;
            }

            // Sync XP from server truth (defensive against missing fields).
            if (resp.xp && typeof resp.xp.total === 'number') {
                // Server returns per-attempt sum (base+bonuses on correct, 0 on
                // wrong). Accumulate locally so the pill shows session total.
                tm.xp = (tm.xp || 0) + resp.xp.total;
                gbTMUpdateXp(tm.xp);
            }

            if (resp.correct === true) {
                if (leftEl) { leftEl.classList.remove('selected'); leftEl.classList.add('correct'); }
                if (rightEl) { rightEl.classList.add('correct'); }

                if (typeof resp.matched_count === 'number') {
                    tm.matched = resp.matched_count;
                } else {
                    tm.matched += 1;
                }
                if (typeof resp.total_pairs === 'number' && resp.total_pairs > 0) {
                    tm.pairsTotal = resp.total_pairs;
                }
                tm.streak += 1;

                const streakBonus = (resp.xp && typeof resp.xp.streak_bonus === 'number') ? resp.xp.streak_bonus : 0;
                gbTMShowToast(streakBonus > 0 ? RT('tm.toast_streak') : RT('tm.toast_correct'), 'correct');
                gbTMUpdateStats();

                setTimeout(function () {
                    if (leftEl) { leftEl.classList.remove('correct'); leftEl.classList.add('matched'); }
                    if (rightEl) { rightEl.classList.remove('correct'); rightEl.classList.add('matched'); }
                    tm.selectedLeft = null;
                    tm.busy = false;

                    if (resp.complete === true) {
                        tm.outcome = resp.outcome || 'cleared';
                        gbTMRenderResult(tm.outcome, resp.completion_bonus_xp || 0);
                        gbTMFinish();
                    }
                }, 520);
                return;
            }

            // Wrong path.
            if (leftEl) leftEl.classList.add('wrong');
            if (rightEl) rightEl.classList.add('wrong');
            tm.wrong += 1;
            tm.streak = 0;

            if (resp.hint) {
                gbTMShowHint(rightEl, resp.hint);
            }

            gbTMShowToast(RT('tm.toast_wrong'), 'wrong');
            gbTMUpdateStats();

            setTimeout(function () {
                if (leftEl) { leftEl.classList.remove('wrong'); leftEl.classList.remove('selected'); }
                if (rightEl) {
                    rightEl.classList.remove('wrong');
                    const hint = rightEl.querySelector('.gb-tm-hint');
                    if (hint) hint.remove();
                }
                tm.selectedLeft = null;
                tm.busy = false;
                if (typeof gbSetButtonNext === 'function') {
                    gbSetButtonNext(RT('tm.dock_select'), /*hidden*/ true);
                }

                if (resp.complete === true) {
                    gbState.tm.outcome = resp.outcome || 'partial';
                    gbTMRenderResult(gbState.tm.outcome, resp.completion_bonus_xp || 0);
                    gbTMFinish();
                }
            }, 1500);
        }

        function gbTMShowHint(rightEl, hintText) {
            if (!rightEl) return;
            const existing = rightEl.querySelector('.gb-tm-hint');
            if (existing) existing.remove();
            const span = document.createElement('span');
            span.className = 'gb-tm-hint';
            span.textContent = RT('tm.hint_correct') + (hintText || '');
            rightEl.appendChild(span);
        }

        function gbTMShowToast(msg, kind) {
            const tm = gbState.tm;
            const el = document.getElementById('gb-tm-toast');
            if (!el) return;
            if (tm && tm._toastTimer) {
                clearTimeout(tm._toastTimer);
                tm._toastTimer = null;
            }
            el.textContent = msg || '';
            el.classList.remove('show');
            // Re-trigger transition.
            void el.offsetWidth;
            el.classList.add('show');
            if (kind) el.setAttribute('data-kind', kind);
            const t = setTimeout(function () {
                el.classList.remove('show');
                if (tm) tm._toastTimer = null;
            }, 2000);
            if (tm) tm._toastTimer = t;
        }

        function gbTMUpdateStats() {
            const tm = gbState.tm;
            const matchedStat = document.getElementById('gb-tm-matched-stat');
            const wrongStat = document.getElementById('gb-tm-wrong-stat');
            const matchedTop = document.getElementById('gb-tm-matched-top');
            const pairsTotal = document.getElementById('gb-tm-pairs-total');
            if (matchedStat) matchedStat.textContent = tm.matched + '/' + tm.pairsTotal;
            if (wrongStat) wrongStat.textContent = String(tm.wrong);
            if (matchedTop) matchedTop.textContent = String(tm.matched);
            if (pairsTotal) pairsTotal.textContent = String(tm.pairsTotal);
        }

        function gbTMUpdateXp(total) {
            const pill = document.getElementById('gb-tm-xp-pill');
            if (pill) pill.textContent = (total || 0) + ' XP';
        }

        function gbTMRenderResult(outcome, completionBonus) {
            const titleEl = document.getElementById('gb-tm-result-title');
            const textEl = document.getElementById('gb-tm-result-text');
            const scoreEl = document.getElementById('gb-tm-score-value');
            const card = document.getElementById('gb-tm-result-card');

            let titleKey;
            let bodyKey;
            switch (outcome) {
                case 'perfect_clear':
                    titleKey = 'tm.result_perfect';
                    bodyKey = 'tm.result_body_perfect';
                    break;
                case 'flawless':
                    titleKey = 'tm.result_flawless';
                    bodyKey = 'tm.result_body_flawless';
                    break;
                case 'cleared':
                    titleKey = 'tm.result_cleared';
                    bodyKey = 'tm.result_body_cleared';
                    break;
                case 'below_threshold':
                case 'partial':
                    titleKey = 'tm.result_not_yet';
                    bodyKey = 'tm.result_body_partial';
                    break;
                default:
                    titleKey = 'tm.result_cleared';
                    bodyKey = 'tm.result_body_cleared';
            }

            if (titleEl) titleEl.textContent = RT(titleKey);
            if (textEl) textEl.textContent = RT(bodyKey);
            const totalXp = (gbState.tm.xp || 0) + (completionBonus || 0);
            if (scoreEl) scoreEl.textContent = totalXp + ' XP';
            if (card) card.classList.add('show');
        }

        function gbTMFinish() {
            gbState.tm.complete = true;
            if (window.__sessionLog) {
                window.__sessionLog.push({
                    phase: 'tile-match', id: 'tm-all',
                    correct: (gbState.tm.outcome === 'perfect_clear' || gbState.tm.outcome === 'flawless' || gbState.tm.outcome === 'cleared'),
                    score: gbState.tm.pairsTotal > 0 ? (gbState.tm.matched / gbState.tm.pairsTotal) : 0,
                    outcome: gbState.tm.outcome,
                });
            }
            if (typeof gbSetButtonNext === 'function') {
                gbSetButtonNext(gbIsLastGame(2) ? RT('btn.next_stage') : RT('btn.next_game'));
            }
        }

        function gbTMAction() {
            // Matching is fully click-driven; the dock button only advances after completion.
            if (gbState.tm && gbState.tm.complete) {
                gbAdvanceFromGame(2, 'gb-panel-tm');
            }
        }

        /* ─────────────────────────────────────────────────────────────────
           REAL-LIFE CHALLENGE (RLC) — 5-step state machine
           Mounts when RLC_CASE is non-null. Otherwise legacy startStage6
           (RL_SCENARIO) flow runs unchanged.
           ───────────────────────────────────────────────────────────────── */
        const rlcState = {
            case: null,
            stepIndex: 0,
            sessionId: null,
            selectedOptionId: null,
            selectedChipId: null,
            reasoningDraft: "",
            stepResults: [],
            rubric: { decision_quality: 0, reasoning_quality: 0, concept_id: 0 },
            busy: false,
            complete: false,
            outcome: null,
            totalXp: 0,
            attemptsByStep: {},
            _toastTimer: null,
        };

        function rlcUuidShort() {
            return 'rlc-' + Date.now().toString(36) + '-' +
                Math.random().toString(36).slice(2, 8);
        }

        function rlcInit() {
            if (!RLC_CASE) return;
            rlcState.case = RLC_CASE;
            rlcState.sessionId = rlcUuidShort();
            rlcState.stepIndex = 0;
            rlcState.selectedOptionId = null;
            rlcState.selectedChipId = null;
            rlcState.reasoningDraft = "";
            rlcState.stepResults = [];
            rlcState.rubric = { decision_quality: 0, reasoning_quality: 0, concept_id: 0 };
            rlcState.busy = false;
            rlcState.complete = false;
            rlcState.outcome = null;
            rlcState.totalXp = 0;
            rlcState.attemptsByStep = {};

            // Static i18n labels in result rubric.
            document.querySelectorAll('#rlc-screen [data-rlc-i18n]').forEach(function (el) {
                const key = el.getAttribute('data-rlc-i18n');
                if (key && typeof RT === 'function') el.textContent = RT(key);
            });

            // Hero copy from RLC_CASE.
            const titleEl = document.getElementById('rlc-title');
            const subtitleEl = document.getElementById('rlc-subtitle');
            const roleBadge = document.getElementById('rlc-role-badge');
            if (titleEl) titleEl.textContent = rlcState.case.title || '';
            if (subtitleEl) subtitleEl.textContent = rlcState.case.intro || '';
            if (roleBadge) {
                const roleKey = 'rlc.role.' + (rlcState.case.expert_role || 'general');
                roleBadge.textContent = (typeof RT === 'function') ? RT(roleKey) : (rlcState.case.expert_role || '');
            }

            // XP pill reset.
            rlcUpdateXpPill();

            // Hide result card on mount.
            const card = document.getElementById('rlc-result-card');
            if (card) card.classList.remove('show');

            // Wire dock button.
            const btn = document.getElementById('rlc-submit-btn');
            if (btn && !btn._rlcWired) {
                btn.addEventListener('click', rlcHandleAction);
                btn._rlcWired = true;
            }

            rlcRenderStep(0);
        }

        function startRLCStage6() {
            // Hide #screen-6 and activate #rlc-screen.
            const allScreens = document.querySelectorAll('.screen');
            allScreens.forEach(function (s) { s.classList.remove('active'); });
            const rlcScreen = document.getElementById('rlc-screen');
            if (rlcScreen) {
                rlcScreen.classList.add('active');
                if (RLC_CASE && RLC_CASE.expert_role) {
                    rlcScreen.setAttribute('data-role', RLC_CASE.expert_role);
                }
            }
            if (typeof setPhaseRequired === 'function') setPhaseRequired('realLife', 5);
            // Timing fix: hold rlc-screen invisible during the announcement
            // (mirrors startStage6 / showConsolidationScreen). The screen is
            // already .active above, so without the opacity-0 hold any
            // pre-rendered step content shows through behind the card.
            if (rlcScreen) { rlcScreen.style.transition = 'none'; rlcScreen.style.opacity = '0'; }
            // Match TM/RL pattern: announce phase, then init.
            if (typeof playPhaseAnnouncement === 'function') {
                playPhaseAnnouncement('phase.real_life', function () {
                    if (rlcScreen) { rlcScreen.style.transition = 'opacity 300ms ease'; rlcScreen.style.opacity = '1'; }
                    rlcInit();
                });
            } else {
                if (rlcScreen) { rlcScreen.style.transition = ''; rlcScreen.style.opacity = ''; }
                rlcInit();
            }
        }

        function rlcRenderStep(idx) {
            if (rlcState.complete) return;
            if (idx < 0 || idx > 4) return;
            rlcState.stepIndex = idx;
            const step = (rlcState.case && rlcState.case.steps) ? rlcState.case.steps[idx] : null;
            if (!step) return;

            // Reset per-step transient inputs.
            rlcState.selectedOptionId = null;
            rlcState.selectedChipId = null;
            if (step.kind === 'reasoning') {
                rlcState.reasoningDraft = "";
            }

            // Toggle .active among the 5 step hosts.
            for (let i = 1; i <= 5; i++) {
                const el = document.getElementById('rlc-step-' + i);
                if (el) el.classList.toggle('active', i === (idx + 1));
            }

            // Update progress dots + counter.
            const dots = document.getElementById('rlc-progress-dots');
            if (dots) {
                const spans = dots.querySelectorAll('span');
                spans.forEach(function (s, i) { s.classList.toggle('active', i === idx); });
            }
            const counter = document.getElementById('rlc-step-counter');
            if (counter) counter.textContent = (idx + 1) + '/5';

            // Stage label per kind via i18n.
            const host = document.getElementById('rlc-step-' + (idx + 1));
            if (host) {
                const labelEl = host.querySelector('[data-rlc-stage-label]');
                const promptEl = host.querySelector('[data-rlc-prompt]');
                if (labelEl && typeof RT === 'function') {
                    const labelKey =
                        step.kind === 'decision' ? 'rlc.step.decision' :
                        step.kind === 'info_request' ? 'rlc.step.info' :
                        step.kind === 'final_decision' ? 'rlc.step.final' :
                        step.kind === 'concept_select' ? 'rlc.step.concept' :
                        'rlc.step.reasoning';
                    labelEl.textContent = RT(labelKey);
                }
                if (promptEl) promptEl.textContent = step.prompt || step.title || '';
                const consEl = host.querySelector('[data-rlc-consequence]');
                if (consEl) { consEl.hidden = true; consEl.textContent = ''; }
            }

            if (step.kind === 'concept_select') {
                rlcRenderConceptStep(step);
            } else if (step.kind === 'reasoning') {
                rlcRenderReasoningStep(step);
            } else {
                rlcRenderDecisionStep(step);
            }

            // Dock label per step kind.
            const dockBtn = document.getElementById('rlc-submit-btn');
            if (dockBtn && typeof RT === 'function') {
                dockBtn.textContent = RT('rlc.dock.submit');
                dockBtn.disabled = true;
            }

            try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (e) { window.scrollTo(0, 0); }
        }

        function rlcRenderDecisionStep(step) {
            const host = document.getElementById('rlc-step-' + (rlcState.stepIndex + 1));
            if (!host) return;
            const optsHost = host.querySelector('[data-rlc-options]');
            if (!optsHost) return;
            optsHost.innerHTML = '';
            const opts = Array.isArray(step.options) ? step.options : [];
            opts.forEach(function (opt) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'rlc-option';
                btn.setAttribute('data-option-id', opt.id || '');
                const labelDiv = document.createElement('div');
                labelDiv.textContent = opt.label || '';
                btn.appendChild(labelDiv);
                // Info-request cost row (time / budget / access).
                if (step.kind === 'info_request' && opt.info_cost && typeof opt.info_cost === 'object') {
                    const row = document.createElement('div');
                    row.className = 'rlc-option-cost';
                    Object.keys(opt.info_cost).forEach(function (k) {
                        const pill = document.createElement('span');
                        pill.className = 'rlc-cost-pill';
                        pill.textContent = k + ': ' + opt.info_cost[k];
                        row.appendChild(pill);
                    });
                    btn.appendChild(row);
                }
                btn.addEventListener('click', function () { rlcSelectOption(opt.id, btn); });
                optsHost.appendChild(btn);
            });
        }

        function rlcRenderConceptStep(step) {
            const host = document.getElementById('rlc-step-' + (rlcState.stepIndex + 1));
            if (!host) return;
            const chipsHost = host.querySelector('[data-rlc-chips]');
            if (!chipsHost) return;
            chipsHost.innerHTML = '';
            const chips = Array.isArray(step.concept_chips) ? step.concept_chips : [];
            chips.forEach(function (chip) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'rlc-chip';
                btn.setAttribute('data-chip-id', chip.id || '');
                btn.textContent = chip.label || '';
                btn.addEventListener('click', function () { rlcSelectChip(chip.id, btn); });
                chipsHost.appendChild(btn);
            });
        }

        function rlcRenderReasoningStep(step) {
            const ta = document.getElementById('rlc-reasoning-textarea');
            const cc = document.getElementById('rlc-reasoning-charcount');
            if (ta) {
                ta.value = "";
                ta.placeholder = (typeof RT === 'function')
                    ? RT('rlc.placeholder.reasoning')
                    : (step.placeholder || '');
                if (!ta._rlcWired) {
                    ta.addEventListener('input', rlcOnReasoningInput);
                    ta._rlcWired = true;
                }
                ta._rlcMinChars = (typeof step.min_chars === 'number' && step.min_chars > 0)
                    ? step.min_chars : 80;
            }
            if (cc) cc.textContent = '0/' + (ta ? ta._rlcMinChars : 80);
        }

        function rlcSelectOption(optionId, el) {
            if (rlcState.busy) return;
            const host = document.getElementById('rlc-step-' + (rlcState.stepIndex + 1));
            if (!host) return;
            host.querySelectorAll('.rlc-option').forEach(function (b) { b.classList.remove('selected'); });
            if (el) el.classList.add('selected');
            rlcState.selectedOptionId = optionId;
            const dockBtn = document.getElementById('rlc-submit-btn');
            if (dockBtn) dockBtn.disabled = false;
        }

        function rlcSelectChip(chipId, el) {
            if (rlcState.busy) return;
            const host = document.getElementById('rlc-step-' + (rlcState.stepIndex + 1));
            if (!host) return;
            host.querySelectorAll('.rlc-chip').forEach(function (b) { b.classList.remove('selected'); });
            if (el) el.classList.add('selected');
            rlcState.selectedChipId = chipId;
            const dockBtn = document.getElementById('rlc-submit-btn');
            if (dockBtn) dockBtn.disabled = false;
        }

        function rlcOnReasoningInput(e) {
            const ta = e && e.target ? e.target : document.getElementById('rlc-reasoning-textarea');
            if (!ta) return;
            const val = ta.value || '';
            rlcState.reasoningDraft = val;
            const minChars = ta._rlcMinChars || 80;
            const cc = document.getElementById('rlc-reasoning-charcount');
            if (cc) cc.textContent = val.length + '/' + minChars;
            const dockBtn = document.getElementById('rlc-submit-btn');
            if (dockBtn) dockBtn.disabled = !(val.length >= minChars);
        }

        async function rlcHandleAction() {
            if (rlcState.busy) return;
            if (rlcState.complete) {
                // Bug RLC-1 fix: previously this branch only called
                // setStage(6.5), which is a label-only setter (updates the
                // progress bar but does NOT navigate). The student was stuck
                // on the RLC result card forever. Match the legacy
                // rlShowEndPlaceholder pattern (~L16384) and route through
                // Consolidation → Boss → Reflection → Results so RLC and
                // legacy Real-Life paths converge to the same downstream
                // navigation. completePhase('realLife') is already called
                // inside rlcRenderResult — we keep a defensive call here in
                // case rlcState.complete was set without going through that
                // renderer.
                if (typeof completePhase === 'function') completePhase('realLife');
                if (typeof setStage === 'function') setStage(6.5);
                if (typeof showConsolidationScreen === 'function' && typeof consolidationHasContent === 'function' && consolidationHasContent()) {
                    showConsolidationScreen(startFinalBoss);
                } else if (typeof startFinalBoss === 'function') {
                    startFinalBoss();
                } else {
                    // Safety: log a warning so a missing downstream renderer
                    // is visible in the console rather than silently freezing
                    // the student on the result card.
                    console.warn('[rlcHandleAction] complete branch: no downstream navigation available (showConsolidationScreen / startFinalBoss missing)');
                }
                return;
            }
            const step = (rlcState.case && rlcState.case.steps) ? rlcState.case.steps[rlcState.stepIndex] : null;
            if (!step) return;

            const payload = {};
            if (step.kind === 'concept_select') {
                if (!rlcState.selectedChipId) return;
                payload.selected_chip_id = rlcState.selectedChipId;
            } else if (step.kind === 'reasoning') {
                if (!rlcState.reasoningDraft) return;
                payload.reasoning_text = rlcState.reasoningDraft;
            } else {
                if (!rlcState.selectedOptionId) return;
                payload.selected_option_id = rlcState.selectedOptionId;
            }

            rlcState.busy = true;
            const dockBtn = document.getElementById('rlc-submit-btn');
            if (dockBtn) dockBtn.disabled = true;

            const resp = await rlcCheckStep(step.id, payload);
            rlcHandleResponse(resp);
        }

        async function rlcCheckStep(stepId, payload) {
            // Single network swap point. Reads ctx.hwId FIRST per TM #140 lesson.
            const ctx = window.NETS_CTX || {};
            const homeworkId = ctx.hwId || ctx.homeworkId || null;
            if (!homeworkId) {
                console.warn('[rlcCheckStep] missing hwId; skipping check');
                return null;
            }
            try {
                const res = await fetch('/api/ai/check-answer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(Object.assign({
                        homework_id: homeworkId,
                        phase: 'real-life-challenge',
                        step_id: stepId,
                        session_id: rlcState.sessionId,
                    }, payload)),
                });
                if (!res.ok) {
                    console.error('[rlcCheckStep] HTTP ' + res.status);
                    return null;
                }
                return await res.json();
            } catch (err) {
                console.error('[rlcCheckStep] network error', err);
                return null;
            }
        }

        function rlcHandleResponse(resp) {
            if (!resp) {
                rlcState.busy = false;
                rlcShowToast((typeof RT === 'function') ? RT('rlc.toast.wrong') : 'Try again', 'wrong');
                const dockBtn = document.getElementById('rlc-submit-btn');
                if (dockBtn) dockBtn.disabled = false;
                return;
            }

            // Accumulate rubric from server-authoritative xp deltas.
            if (resp.xp && typeof resp.xp === 'object') {
                if (typeof resp.xp.decision_quality === 'number') {
                    rlcState.rubric.decision_quality += resp.xp.decision_quality;
                }
                if (typeof resp.xp.reasoning_quality === 'number') {
                    rlcState.rubric.reasoning_quality += resp.xp.reasoning_quality;
                }
                if (typeof resp.xp.concept_id === 'number') {
                    rlcState.rubric.concept_id += resp.xp.concept_id;
                }
            }
            rlcUpdateXpPill();

            const stepKind = resp.kind || (rlcState.case && rlcState.case.steps[rlcState.stepIndex] ?
                rlcState.case.steps[rlcState.stepIndex].kind : '');
            const stepId = resp.step_id || (rlcState.case && rlcState.case.steps[rlcState.stepIndex] ?
                rlcState.case.steps[rlcState.stepIndex].id : '');
            const isDecisionLike =
                stepKind === 'decision' || stepKind === 'info_request' || stepKind === 'final_decision';

            // Wrong decision: track attempts; on 2nd wrong, reveal correct option.
            if (isDecisionLike && resp.correct === false) {
                rlcState.attemptsByStep[stepId] = (rlcState.attemptsByStep[stepId] || 0) + 1;

                // Render consequence under options if returned.
                const host = document.getElementById('rlc-step-' + (rlcState.stepIndex + 1));
                if (host && resp.consequence) {
                    const consEl = host.querySelector('[data-rlc-consequence]');
                    if (consEl) {
                        const prefix = (typeof RT === 'function') ? RT('rlc.consequence_reveal') + ' ' : '';
                        consEl.textContent = prefix + resp.consequence;
                        consEl.hidden = false;
                    }
                }

                if (rlcState.attemptsByStep[stepId] >= 2 && resp.correct_option_label) {
                    // Pedagogical reveal — lock all options, mark the correct one, advance after delay.
                    if (host) {
                        const allBtns = host.querySelectorAll('.rlc-option');
                        allBtns.forEach(function (b) {
                            b.classList.add('locked');
                            const labelEl = b.firstElementChild;
                            const txt = labelEl ? labelEl.textContent : b.textContent;
                            if ((txt || '').trim() === (resp.correct_option_label || '').trim()) {
                                b.classList.remove('locked');
                                b.classList.add('is-correct-revealed');
                            }
                        });
                    }
                    rlcShowToast((typeof RT === 'function') ? RT('rlc.toast.locked') : 'Locked', 'wrong');
                    setTimeout(function () {
                        rlcState.busy = false;
                        if (typeof resp.step_index === 'number') {
                            if (resp.complete === true) {
                                rlcState.complete = true;
                                rlcState.outcome = resp.outcome || null;
                                rlcState.totalXp = resp.total_xp || 0;
                                rlcRenderResult();
                            } else {
                                rlcRenderStep((resp.step_index || rlcState.stepIndex) + 1);
                            }
                        } else {
                            rlcRenderStep(rlcState.stepIndex + 1);
                        }
                    }, 1500);
                    return;
                }

                // First wrong attempt — let student retry.
                rlcShowToast((typeof RT === 'function') ? RT('rlc.toast.try_again') : 'Try again', 'wrong');
                rlcState.busy = false;
                const dockBtn = document.getElementById('rlc-submit-btn');
                if (dockBtn) dockBtn.disabled = false;
                return;
            }

            // Correct decision / concept / reasoning response.
            rlcState.stepResults.push(resp);
            rlcShowToast((typeof RT === 'function') ? RT('rlc.toast.correct') : 'Nice', 'correct');

            if (resp.complete === true) {
                rlcState.busy = false;
                rlcState.complete = true;
                rlcState.outcome = resp.outcome || null;
                rlcState.totalXp = resp.total_xp || 0;
                if (resp.rubric_breakdown && typeof resp.rubric_breakdown === 'object') {
                    rlcState.rubric.decision_quality = resp.rubric_breakdown.decision_quality || rlcState.rubric.decision_quality;
                    rlcState.rubric.reasoning_quality = resp.rubric_breakdown.reasoning_quality || rlcState.rubric.reasoning_quality;
                    rlcState.rubric.concept_id = resp.rubric_breakdown.concept_id || rlcState.rubric.concept_id;
                }
                rlcRenderResult();
                return;
            }

            // Advance to next step.
            const nextIdx = (typeof resp.step_index === 'number') ? resp.step_index + 1 : rlcState.stepIndex + 1;
            setTimeout(function () {
                rlcState.busy = false;
                rlcRenderStep(nextIdx);
            }, 350);
        }

        function rlcRenderResult() {
            const card = document.getElementById('rlc-result-card');
            const titleEl = document.getElementById('rlc-result-title');
            const dec = document.getElementById('rlc-rubric-decision');
            const reas = document.getElementById('rlc-rubric-reasoning');
            const conc = document.getElementById('rlc-rubric-concept');
            const bonusRow = document.getElementById('rlc-rubric-bonus-row');
            const bonus = document.getElementById('rlc-rubric-bonus');
            const total = document.getElementById('rlc-rubric-total');

            if (titleEl) {
                const key = 'rlc.outcome.' + (rlcState.outcome || 'passing');
                titleEl.textContent = (typeof RT === 'function') ? RT(key) : (rlcState.outcome || '');
            }
            if (dec) dec.textContent = String(rlcState.rubric.decision_quality || 0);
            if (reas) reas.textContent = String(rlcState.rubric.reasoning_quality || 0);
            if (conc) conc.textContent = String(rlcState.rubric.concept_id || 0);

            const lastResp = rlcState.stepResults[rlcState.stepResults.length - 1] || {};
            const bonusXp = (lastResp.completion_bonus_xp || 0);
            if (bonus) bonus.textContent = String(bonusXp);
            if (bonusRow) bonusRow.hidden = !(bonusXp > 0);

            if (total) total.textContent = String(rlcState.totalXp || 0);

            if (card) card.classList.add('show');

            if (typeof completePhase === 'function') completePhase('realLife');

            if (window.__sessionLog) {
                try {
                    window.__sessionLog.push({
                        phase: 'real-life-challenge',
                        id: (rlcState.case && rlcState.case.id) ? rlcState.case.id : 'rlc',
                        outcome: rlcState.outcome,
                        total_xp: rlcState.totalXp,
                    });
                } catch (e) { /* noop */ }
            }

            const dockBtn = document.getElementById('rlc-submit-btn');
            if (dockBtn && typeof RT === 'function') {
                dockBtn.textContent = RT('rlc.dock.finish');
                dockBtn.disabled = false;
            }
        }

        function rlcShowToast(msg, kind) {
            const el = document.getElementById('rlc-toast');
            if (!el) return;
            if (rlcState._toastTimer) {
                clearTimeout(rlcState._toastTimer);
                rlcState._toastTimer = null;
            }
            el.textContent = msg || '';
            el.classList.remove('show');
            void el.offsetWidth;
            if (kind) el.setAttribute('data-kind', kind);
            el.classList.add('show');
            const t = setTimeout(function () {
                el.classList.remove('show');
                rlcState._toastTimer = null;
            }, 1800);
            rlcState._toastTimer = t;
        }

        function rlcUpdateXpPill() {
            const pill = document.getElementById('rlc-xp-pill');
            if (!pill) return;
            const r = rlcState.rubric || {};
            const cum = (r.decision_quality || 0) + (r.reasoning_quality || 0) + (r.concept_id || 0);
            pill.textContent = cum + ' XP';
        }

        // ── PUZZLE LOCK — linear solve-stepper (PR A 2026-05-07) ─────────
        // Replaces the prior 15-style sliding-tile implementation. Real
        // demo data (HW-20260505-005, HW-20260505-009) ships items as a
        // sequential proof/factoring chain {content, q, a}; the student
        // now solves them in order, one slot active at a time.
        //
        // State model:
        //   pl.tiles        — input items in original order
        //   pl.total        — pl.tiles.length
        //   pl.currentStep  — index of the active step (0..total-1)
        //   pl.complete     — true once currentStep === total
        //   pl.busy         — input lock during animation/feedback
        //   pl.wrongCount   — running counter for session log
        //
        // Answer matching mirrors gbAQAction's dual-pass from PR #165:
        // legacy whitespace-stripped lowercase first, then the shared
        // window.mathNormalize for math-equivalent forms (α/alfa/alpha,
        // tg/tan, U+2212/-, decimal comma/dot, "lhs = rhs" prefix).
        function gbInitPL() {
            const pl = gbState.pl;
            const items = Array.isArray(GB_PUZZLE_LOCK) ? GB_PUZZLE_LOCK : [];
            pl.tiles = items.slice(0, 15).map(function (t) {
                return {
                    content: (t && t.content) || '',
                    q:       (t && t.q)       || '',
                    a:       (t && t.a)       || '',
                    hint:    (t && t.hint)    || '',
                };
            });
            pl.total = pl.tiles.length;
            pl.currentStep = 0;
            pl.wrongCount = 0;
            pl.complete = pl.total === 0;
            pl.busy = false;
            // Legacy fields kept around so any external accessors don't crash;
            // they are no longer consulted by render or action.
            pl.size = 0;
            pl.cells = [];
            pl.emptyIdx = -1;
            pl.correct = 0;
            pl.selected = null;

            const winBanner = document.getElementById('gb-pl-win-banner');
            if (winBanner) winBanner.classList.remove('show');
            const fb = document.getElementById('gb-pl-feedback');
            if (fb) { fb.classList.remove('show'); fb.textContent = ''; }

            gbPLRender();
            gbPLUpdateStatus();
            gbPLPrimeButton();
        }

        function gbPLPrimeButton() {
            // Linear stepper always offers a clickable Confirm CTA when there's
            // an active step. No more "waiting for tile selection" gap.
            if (typeof btn === 'undefined' || !btn) return;
            const pl = gbState.pl;
            if (pl.complete) return;  // gbPLWin will set the next-game label
            btn.classList.remove('state-line', 'pulse');
            btn.classList.add('state-pill', 'pulse');
            setBtnText(RT('btn.confirm'));
        }

        // Authored content carries <b>Qadam N.</b> markup that must render
        // as HTML to read naturally. This helper mirrors how the rest of
        // the runtime injects authored homework content (fc-definition,
        // panel blocks, tile-match text) — same trust model: the JSON is
        // server-side authored, never student-typed.
        function gbPLSetCellContent(node, html) {
            // Use insertAdjacentHTML for parity with the existing safe-HTML
            // pattern across the runtime; clearing first avoids a duplicate
            // append when this helper is called twice on the same node.
            while (node.firstChild) node.removeChild(node.firstChild);
            node.insertAdjacentHTML('afterbegin', String(html || ''));
        }

        function gbPLRender() {
            const pl = gbState.pl;
            const grid = document.getElementById('gb-pl-grid');
            if (!grid) return;
            // Reset any inline grid-template style left over from the old
            // sliding-mechanic render, so the CSS `flex-direction: column`
            // on .gb-pl-grid wins on re-init.
            grid.style.gridTemplateColumns = '';
            while (grid.firstChild) grid.removeChild(grid.firstChild);
            pl.tiles.forEach(function (tile, idx) {
                const card = document.createElement('div');
                card.className = 'gb-pl-cell';
                card.dataset.idx = String(idx);
                card.dataset.stepNum = String(idx + 1);
                // No click handler — the active step is driven by the
                // dedicated input + #action-button below the stepper.
                let stateClass;
                if (idx < pl.currentStep)        stateClass = 'solved';
                else if (idx === pl.currentStep) stateClass = 'active';
                else                              stateClass = 'locked';
                card.classList.add(stateClass);

                const body = document.createElement('div');
                body.className = 'gb-pl-cell-body';
                if (stateClass === 'locked') {
                    // Future steps stay hidden by content — only the lock
                    // glyph and dashed border tell the student "later".
                    body.textContent = RT('pl.step_locked');
                } else {
                    // Active and solved both show the step content. Authored
                    // HTML markup (<b>Qadam N.</b>) preserved.
                    gbPLSetCellContent(body, tile.content);
                }
                card.appendChild(body);
                grid.appendChild(card);
            });

            // Drive the question box off the active step.
            const qBox = document.getElementById('gb-pl-question-box');
            const qText = document.getElementById('gb-pl-question');
            const qInput = document.getElementById('gb-pl-input');
            const fb = document.getElementById('gb-pl-feedback');
            if (pl.complete) {
                if (qBox) qBox.classList.remove('show');
                return;
            }
            const active = pl.tiles[pl.currentStep];
            if (!active) {
                if (qBox) qBox.classList.remove('show');
                return;
            }
            if (qText) qText.textContent = active.q || RT('pl.no_question');
            if (qInput) {
                qInput.value = '';
                qInput.disabled = false;
                qInput.style.borderColor = '';
                qInput.classList.remove('shake');
            }
            if (fb) { fb.classList.remove('show'); fb.textContent = ''; }
            if (qBox) qBox.classList.add('show');
        }

        function gbPLUpdateStatus() {
            const st = document.getElementById('gb-pl-status');
            if (!st) return;
            const pl = gbState.pl;
            // i18n template — "Qadam {n} / {total}". Falls back gracefully
            // if the locale missed the key (would render the placeholder).
            const tmpl = RT('pl.step_status') || 'Qadam {n} / {total}';
            const done = Math.min(pl.currentStep, pl.total);
            st.textContent = tmpl.replace('{n}', String(done)).replace('{total}', String(pl.total));
        }

        // PL-04: dual-pass match (legacy + mathNormalize) at parity with PR #165.
        function gbPLAnswerMatches(userVal, expected) {
            const norm = function (s) { return String(s == null ? '' : s).toLowerCase().replace(/\s+/g, '').trim(); };
            const userN = norm(userVal);
            const expectedN = norm(expected);
            if (!expectedN) return false;
            if (userN === expectedN) return true;
            // Math-equivalence: same canonical form via the shared normalizer.
            if (typeof window.mathNormalize === 'function') {
                const um = window.mathNormalize(userVal);
                const em = window.mathNormalize(expected);
                if (um && um === em) return true;
            }
            // Loose include for partial-form answers (legacy behavior).
            if (expectedN.length > 3 && expectedN.includes(userN)) return true;
            if (userN.length     > 3 && userN.includes(expectedN)) return true;
            return false;
        }

        function gbPLAction() {
            const pl = gbState.pl;
            if (pl.complete || pl.busy) return;
            const qInput = document.getElementById('gb-pl-input');
            const userVal = qInput ? qInput.value.trim() : '';
            if (!userVal) {
                if (qInput) {
                    qInput.style.borderColor = '#d9534f';
                    setTimeout(function () { qInput.style.borderColor = ''; }, 1200);
                }
                return;
            }
            const tile = pl.tiles[pl.currentStep];
            if (!tile) return;

            pl.busy = true;
            if (qInput) qInput.disabled = true;

            const isOk = gbPLAnswerMatches(userVal, tile.a);

            if (isOk) {
                pl.currentStep += 1;
                if (pl.currentStep >= pl.total) {
                    pl.complete = true;
                    gbPLRender();
                    gbPLUpdateStatus();
                    gbPLWin();
                    return;
                }
                // Brief pause so the previous step gets to flash green
                // before we re-render with the next active step.
                setTimeout(function () {
                    pl.busy = false;
                    gbPLRender();
                    gbPLUpdateStatus();
                    gbPLPrimeButton();
                    const inp2 = document.getElementById('gb-pl-input');
                    if (inp2) setTimeout(function () { inp2.focus(); }, 60);
                }, 380);
                return;
            }

            // Wrong path — stay on the same step, surface the authored hint.
            pl.wrongCount += 1;
            const fb = document.getElementById('gb-pl-feedback');
            if (fb) {
                fb.textContent = (tile.hint && String(tile.hint).trim()) || RT('pl.wrong_feedback');
                fb.classList.add('show');
            }
            if (qInput) {
                qInput.style.borderColor = '#d9534f';
                qInput.classList.add('shake');
            }
            const activeCard = document.querySelector('#gb-pl-grid .gb-pl-cell.active');
            if (activeCard) {
                activeCard.classList.add('wrong-flash');
                setTimeout(function () { activeCard.classList.remove('wrong-flash'); }, 600);
            }
            setTimeout(function () {
                pl.busy = false;
                if (qInput) {
                    qInput.disabled = false;
                    qInput.style.borderColor = '';
                    qInput.classList.remove('shake');
                    qInput.focus();
                }
            }, 700);
        }

        function gbPLWin() {
            const pl = gbState.pl;
            pl.complete = true;
            const banner = document.getElementById('gb-pl-win-banner');
            if (banner) banner.classList.add('show');
            const qBox = document.getElementById('gb-pl-question-box');
            if (qBox) qBox.classList.remove('show');
            if (window.__sessionLog) {
                window.__sessionLog.push({
                    phase: 'puzzle-lock', id: 'pl-all',
                    correct: true, score: 1,
                });
            }
            // Registry decides next game on click; we just label the button.
            if (typeof btn !== 'undefined' && btn) {
                btn.classList.remove('state-line');
                btn.classList.add('state-pill', 'pulse');
            }
            gbSetButtonNext(gbIsLastGame(3) ? RT('btn.next_stage') : RT('btn.next_game'));
        }

        // ── Mystery Box (sub-game 5) — interleaved category recognition ───
        function gbInitMB() {
            const mb = gbState.mb;
            const items = Array.isArray(GB_MYSTERY_BOX) ? GB_MYSTERY_BOX : [];
            mb.boxes = items.map(item => ({
                category: String(item && item.category || ''),
                q: String(item && item.q || ''),
                a: String(item && item.a || ''),
            }));
            // Picker labels: prefer pre-computed labels[] (from injector), fall
            // back to deriving from boxes' categories so the runtime still
            // works on hand-crafted fixtures without the adapter.
            const fromAdapter = (items[0] && Array.isArray(items[0].labels)) ? items[0].labels : null;
            if (fromAdapter && fromAdapter.length) {
                mb.labels = fromAdapter.slice();
            } else {
                const seen = [];
                mb.boxes.forEach(b => {
                    const c = (b.category || '').trim();
                    if (c && seen.indexOf(c) === -1) seen.push(c);
                });
                mb.labels = seen;
            }
            mb.opened = new Array(mb.boxes.length).fill(null); // null = closed, 'correct'/'partial'/'wrong' = opened state
            mb.idx = -1;
            mb.phase = 'select';
            mb.pickedLabel = '';
            mb.idCorrect = null;
            mb.ansCorrect = null;
            mb.complete = false;
            mb.busy = false;
            gbMBRender();
            gbMBUpdateStatus();
            // Hide stages and banner on init.
            const idStage = document.getElementById('gb-mb-identify');
            const solveStage = document.getElementById('gb-mb-solve');
            const banner = document.getElementById('gb-mb-win-banner');
            if (idStage) idStage.classList.remove('show');
            if (solveStage) solveStage.classList.remove('show');
            if (banner) banner.classList.remove('show');
            // Button stays inert until a box is clicked.
            btn.classList.remove('pulse','state-pill','state-line');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
        }

        function gbMBUpdateStatus() {
            const mb = gbState.mb;
            const opened = mb.opened.filter(s => s !== null).length;
            const total = mb.boxes.length;
            const st = document.getElementById('gb-mb-status');
            if (st) st.textContent = RT('mb.boxes_status') + ' ' + opened + ' / ' + total;
        }

        function gbMBRender() {
            const mb = gbState.mb;
            const board = document.getElementById('gb-mb-board');
            if (!board) return;
            const html = mb.boxes.map((b, i) => {
                const opened = mb.opened[i];
                const cls = 'gb-mb-box' + (opened ? ' opened' : '');
                const mark = opened === 'correct' ? '<span class="gb-mb-box-mark correct">✓</span>'
                          : opened === 'partial' ? '<span class="gb-mb-box-mark correct">◐</span>'
                          : opened === 'wrong'   ? '<span class="gb-mb-box-mark wrong">✗</span>'
                          : '';
                return '<div class="' + cls + '" data-mb-idx="' + i + '">'
                     + '<span class="gb-mb-box-num">#' + (i + 1) + '</span>'
                     + '📦' + mark
                     + '</div>';
            }).join('');
            board.innerHTML = html;
            board.querySelectorAll('.gb-mb-box').forEach(el => {
                el.onclick = () => {
                    if (gbState.mb.busy) return;
                    if (gbState.mb.phase !== 'select') return;
                    const idx = Number(el.dataset.mbIdx);
                    if (Number.isFinite(idx) && gbState.mb.opened[idx] === null) {
                        gbMBOpenBox(idx);
                    }
                };
            });
        }

        function gbMBOpenBox(idx) {
            const mb = gbState.mb;
            mb.idx = idx;
            mb.phase = 'identify';
            mb.idCorrect = null;
            mb.ansCorrect = null;
            mb.pickedLabel = '';
            const idStage = document.getElementById('gb-mb-identify');
            const labelsHost = document.getElementById('gb-mb-labels');
            const fb = document.getElementById('gb-mb-id-feedback');
            if (fb) { fb.textContent = ''; fb.className = 'gb-mb-feedback'; }
            if (labelsHost) {
                // Build via DOM methods so author-provided strings can't
                // smuggle markup into the chip. Also: when the label
                // string is empty, provide an explicit "Variant N"
                // accessible name so screen readers don't announce an
                // empty button.
                while (labelsHost.firstChild) labelsHost.removeChild(labelsHost.firstChild);
                mb.labels.forEach((l, i) => {
                    const raw = String(l == null ? '' : l);
                    const fallback = 'Variant ' + (i + 1);
                    const btn = document.createElement('button');
                    btn.className = 'gb-mb-label';
                    btn.type = 'button';
                    btn.dataset.mbLabel = raw;
                    btn.setAttribute('aria-label', raw || fallback);
                    if (raw) {
                        btn.textContent = raw;
                    } else {
                        const ph = document.createElement('span');
                        ph.setAttribute('aria-hidden', 'true');
                        ph.textContent = fallback;
                        btn.appendChild(ph);
                    }
                    btn.addEventListener('click', () => gbMBPickLabel(btn.dataset.mbLabel || ''));
                    labelsHost.appendChild(btn);
                });
            }
            if (idStage) idStage.classList.add('show');
            // Edge case: only one label (or zero) — auto-pick to keep the flow moving.
            if (!mb.labels.length) {
                gbMBPickLabel('');
            } else if (mb.labels.length === 1) {
                gbMBPickLabel(mb.labels[0]);
            }
        }

        function gbMBPickLabel(label) {
            const mb = gbState.mb;
            if (mb.phase !== 'identify') return;
            mb.pickedLabel = label || '';
            const truth = (mb.boxes[mb.idx] && mb.boxes[mb.idx].category || '').trim();
            mb.idCorrect = (mb.pickedLabel.trim() === truth) || (!truth && !mb.pickedLabel);
            // Highlight: picked button + the truth (if different from picked).
            const labelsHost = document.getElementById('gb-mb-labels');
            if (labelsHost) {
                labelsHost.querySelectorAll('.gb-mb-label').forEach(el => {
                    el.disabled = true;
                    const v = el.dataset.mbLabel || '';
                    if (v === mb.pickedLabel) {
                        el.classList.add(mb.idCorrect ? 'picked-correct' : 'picked-wrong');
                    } else if (!mb.idCorrect && v === truth) {
                        el.classList.add('picked-truth');
                    }
                });
            }
            const fb = document.getElementById('gb-mb-id-feedback');
            if (fb) {
                fb.textContent = mb.idCorrect ? RT('mb.right_category') : (RT('mb.actually_prefix') + (truth || '—'));
                fb.className = 'gb-mb-feedback ' + (mb.idCorrect ? 'correct' : 'wrong');
            }
            // Advance to solve stage after a brief beat so the student sees the ID feedback.
            mb.busy = true;
            setTimeout(() => {
                mb.phase = 'solve';
                mb.busy = false;
                const solveStage = document.getElementById('gb-mb-solve');
                const prompt = document.getElementById('gb-mb-solve-prompt');
                const input = document.getElementById('gb-mb-solve-input');
                const sfb = document.getElementById('gb-mb-solve-feedback');
                if (prompt) prompt.innerHTML = (mb.boxes[mb.idx] && mb.boxes[mb.idx].q) || '';
                if (input) { input.value = ''; input.disabled = false; }
                if (sfb) { sfb.textContent = ''; sfb.className = 'gb-mb-feedback'; }
                if (solveStage) solveStage.classList.add('show');
                if (input) input.focus();
                gbSetButtonForMB(RT('btn.submit_answer'));
            }, 700);
        }

        function gbMBSubmitAnswer() {
            const mb = gbState.mb;
            if (mb.phase !== 'solve' || mb.busy) return;
            const input = document.getElementById('gb-mb-solve-input');
            const userVal = input ? input.value.trim() : '';
            const truth = (mb.boxes[mb.idx] && mb.boxes[mb.idx].a || '').trim();
            const norm = s => String(s == null ? '' : s).toLowerCase().replace(/\s+/g, ' ').trim();
            mb.ansCorrect = norm(userVal) === norm(truth);
            // Outcome label: correct ID + correct ans = correct; correct ID + wrong = partial;
            // wrong ID + correct ans = partial (lucky guess); wrong ID + wrong = wrong.
            let outcome;
            if (mb.idCorrect && mb.ansCorrect) outcome = 'correct';
            else if (mb.idCorrect && !mb.ansCorrect) outcome = 'partial';
            else if (!mb.idCorrect && mb.ansCorrect) outcome = 'partial';
            else outcome = 'wrong';
            mb.opened[mb.idx] = outcome;
            mb.phase = 'feedback';
            const sfb = document.getElementById('gb-mb-solve-feedback');
            if (sfb) {
                let msg;
                if (outcome === 'correct') msg = RT('mb.outcome_correct');
                else if (outcome === 'partial' && mb.ansCorrect) msg = RT('mb.outcome_part_ans');
                else if (outcome === 'partial') msg = RT('mb.outcome_part_cat') + (truth || '—');
                else msg = RT('mb.outcome_wrong') + (truth || '—');
                sfb.textContent = msg;
                sfb.className = 'gb-mb-feedback ' + outcome;
            }
            if (input) input.disabled = true;
            if (window.__sessionLog) {
                window.__sessionLog.push({
                    phase: 'mystery-box',
                    id: 'mb-' + (mb.idx + 1),
                    correct: outcome === 'correct',
                    score: outcome === 'correct' ? 1 : (outcome === 'partial' ? 0.5 : 0),
                });
            }
            gbMBRender();
            gbMBUpdateStatus();
            const remaining = mb.opened.filter(s => s === null).length;
            gbSetButtonForMB(remaining > 0 ? RT('btn.next_box') : RT('btn.complete'));
        }

        function gbMBNextBox() {
            const mb = gbState.mb;
            mb.phase = 'select';
            mb.idx = -1;
            const idStage = document.getElementById('gb-mb-identify');
            const solveStage = document.getElementById('gb-mb-solve');
            if (idStage) idStage.classList.remove('show');
            if (solveStage) solveStage.classList.remove('show');
            const remaining = mb.opened.filter(s => s === null).length;
            if (remaining === 0) {
                gbMBWin();
                return;
            }
            // Button goes inert; user clicks another box to continue.
            btn.classList.remove('pulse','state-pill','state-line');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
        }

        function gbMBWin() {
            const mb = gbState.mb;
            mb.complete = true;
            const banner = document.getElementById('gb-mb-win-banner');
            if (banner) banner.classList.add('show');
            if (window.__sessionLog) {
                const correctCount = mb.opened.filter(s => s === 'correct').length;
                window.__sessionLog.push({
                    phase: 'mystery-box', id: 'mb-all',
                    correct: correctCount === mb.boxes.length,
                    score: mb.boxes.length ? (correctCount / mb.boxes.length) : 0,
                });
            }
            // Registry decides exit on click; just label the button.
            gbSetButtonNext(RT('btn.next_stage'));
        }

        function gbSetButtonForMB(text) {
            btn.classList.remove('pulse','state-pill','state-line');
            btn.classList.add('state-pill');
            setBtnText(text || RT('btn.continue'));
            btn.classList.add('pulse');
        }

        function gbMBAction() {
            const mb = gbState.mb;
            if (mb.phase === 'solve') { gbMBSubmitAnswer(); return; }
            if (mb.phase === 'feedback') { gbMBNextBox(); return; }
            // 'select' or 'identify' — button is inert; clicks come from board / labels.
        }

        // ── PHASE 3 · TIC TAC TOE vs AI ──────────────────────────────────
        // 3 games per session. Student is X (always first). Tap-before-question:
        // student taps a cell, then a MC question appears. Correct → mark lands
        // on intended cell. Wrong → mark lands on a random empty cell. AI plays
        // optimally (minimax) — best student outcome is a draw.

        const GB_TTT_LINES = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];

        // Pure logic helpers — preserved from previous TTT runtime.
        function gbTTTWinner(board) {
            for (const line of GB_TTT_LINES) {
                const [a,b,c] = line;
                if (board[a] && board[a] === board[b] && board[a] === board[c]) {
                    return { mark: board[a], line: line };
                }
            }
            return null;
        }

        function gbTTTBoardFull(board) {
            return board.every(c => c !== '');
        }

        function gbTTTScore(board, player) {
            const w = gbTTTWinner(board);
            if (w) return w.mark === player ? 1 : -1;
            if (gbTTTBoardFull(board)) return 0;
            const opp = player === 'X' ? 'O' : 'X';
            let best = -Infinity;
            for (let i = 0; i < 9; i++) {
                if (board[i]) continue;
                board[i] = player;
                const s = -gbTTTScore(board, opp);
                board[i] = '';
                if (s > best) best = s;
            }
            return best;
        }

        function gbTTTBestMove(board, player) {
            const opp = player === 'X' ? 'O' : 'X';
            let bestScore = -Infinity, bestMove = -1;
            for (let i = 0; i < 9; i++) {
                if (board[i]) continue;
                board[i] = player;
                const s = -gbTTTScore(board, opp);
                board[i] = '';
                if (s > bestScore) { bestScore = s; bestMove = i; }
            }
            return bestMove;
        }

        // Sequential picker — items already shuffled side-disjoint server-side.
        function gbTTTPickItem() {
            const items = Array.isArray(GB_TTT) ? GB_TTT : [];
            if (items.length === 0) return null;
            const ttt = gbState.ttt;
            const item = items[ttt.currentItemIdx % items.length];
            ttt.currentItemIdx++;
            ttt.currentItemId = (item && item.id) || null;
            return item;
        }

        // Single network swap-point #1 — per-pick grading.
        // Mirrors gbTMCheckPair (PR #140); uses canonical 3-key chain for hwId.
        async function gbTTTCheckAnswer(itemId, picked) {
            const ctx = window.NETS_CTX || {};
            const homeworkId = ctx.hwId || ctx.homework_id || ctx.homeworkId || null;
            if (!homeworkId) {
                console.warn('[gbTTTCheckAnswer] missing homework_id; soft-fail');
                return { is_correct: false, mercy: false, xp_delta: 0, correct_value: null };
            }
            try {
                const res = await fetch('/api/ai/check-answer?phase=ttt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        phase: 'ttt',
                        homework_id: homeworkId,
                        item_id: itemId,
                        picked: picked,
                    }),
                });
                if (!res.ok) {
                    console.error('[gbTTTCheckAnswer] HTTP ' + res.status);
                    return { is_correct: false, mercy: false, xp_delta: 0, correct_value: null };
                }
                return await res.json();
            } catch (err) {
                console.error('[gbTTTCheckAnswer] network error', err);
                return { is_correct: false, mercy: false, xp_delta: 0, correct_value: null };
            }
        }

        // Single network swap-point #2 — end-of-session tally.
        async function gbTTTSessionFinalize() {
            const ctx = window.NETS_CTX || {};
            const homeworkId = ctx.hwId || ctx.homework_id || ctx.homeworkId || null;
            const ttt = gbState.ttt;
            const results = (ttt.games || []).map(o => ({ outcome: o }));
            if (!homeworkId) {
                console.warn('[gbTTTSessionFinalize] missing homework_id; soft-fail');
                return { session_xp: 0, strong_session_bonus: 0, mastery_tier: 'Working Toward Holding Ground', duolingo_remediation: false };
            }
            try {
                const res = await fetch('/api/ai/check-answer?phase=ttt-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        phase: 'ttt-session',
                        homework_id: homeworkId,
                        results: results,
                    }),
                });
                if (!res.ok) {
                    console.error('[gbTTTSessionFinalize] HTTP ' + res.status);
                    return { session_xp: 0, strong_session_bonus: 0, mastery_tier: 'Working Toward Holding Ground', duolingo_remediation: false };
                }
                return await res.json();
            } catch (err) {
                console.error('[gbTTTSessionFinalize] network error', err);
                return { session_xp: 0, strong_session_bonus: 0, mastery_tier: 'Working Toward Holding Ground', duolingo_remediation: false };
            }
        }

        function gbTTTRender() {
            const ttt = gbState.ttt;
            const board = document.getElementById('gb-ttt-board');
            if (!board) return;
            const winSet = ttt.winLine ? new Set(ttt.winLine) : null;
            board.innerHTML = '';
            for (let i = 0; i < 9; i++) {
                const cell = document.createElement('button');
                cell.className = 'gb-ttt-cell';
                cell.type = 'button';
                cell.setAttribute('data-cell-idx', String(i));
                cell.setAttribute('role', 'gridcell');
                const mark = ttt.board[i];
                if (mark) {
                    cell.classList.add('filled');
                    cell.classList.add(mark === 'X' ? 'x' : 'o');
                    const span = document.createElement('span');
                    span.className = 'gb-ttt-mark ' + (mark === 'X' ? 'x' : 'o');
                    span.textContent = mark;
                    cell.appendChild(span);
                }
                if (winSet && winSet.has(i)) cell.classList.add('win');
                if (i === ttt.pendingCellIdx && !mark) cell.classList.add('pending');
                if (ttt.phase !== 'await-tap' || ttt.busy) cell.classList.add('locked');
                if (!mark && ttt.phase === 'await-tap' && !ttt.busy) {
                    cell.addEventListener('click', () => gbTTTCellClick(i));
                }
                board.appendChild(cell);
            }
            // Hero / stats / pills.
            const counter = document.getElementById('gb-ttt-counter');
            if (counter) counter.textContent = "O'yin " + (ttt.gameNum + 1) + " / 3";
            const gamePill = document.getElementById('gb-ttt-game-pill');
            if (gamePill) gamePill.textContent = 'Game ' + (ttt.gameNum + 1) + '/3';
            const drawsEl = document.getElementById('gb-ttt-draws');
            if (drawsEl) drawsEl.textContent = String(ttt.draws);
            const lossesEl = document.getElementById('gb-ttt-losses');
            if (lossesEl) lossesEl.textContent = String(ttt.losses);
            const correctEl = document.getElementById('gb-ttt-correct');
            if (correctEl) correctEl.textContent = String(ttt.correct);
            const turnPill = document.getElementById('gb-ttt-turn-pill');
            const boardCopy = document.getElementById('gb-ttt-board-copy');
            if (turnPill && boardCopy) {
                if (ttt.phase === 'await-tap') {
                    turnPill.textContent = RT('ttt.turnYour');
                    boardCopy.textContent = RT('ttt.boardCopy');
                } else if (ttt.phase === 'awaiting-answer') {
                    turnPill.textContent = RT('ttt.turnAnswer');
                    boardCopy.textContent = RT('ttt.boardCopyAnswer');
                } else if (ttt.phase === 'ai-thinking') {
                    turnPill.textContent = RT('ttt.turnAI');
                    boardCopy.textContent = RT('ttt.boardCopyAI');
                } else if (ttt.phase === 'game-over') {
                    turnPill.textContent = 'Game ' + (ttt.gameNum + 1);
                }
            }
        }

        function gbInitTTT() {
            // Generate a short uuid-ish session id.
            const sessionId = 'ttt-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
            gbState.ttt = {
                sessionId: sessionId,
                board: Array(9).fill(''),
                games: [],
                gameNum: 0,
                draws: 0,
                losses: 0,
                correct: 0,
                pendingCellIdx: -1,
                currentItemIdx: 0,
                currentItemId: null,
                phase: 'await-tap',
                busy: false,
                complete: false,
                winLine: null,
                lastResolveTimer: null,
            };
            // Hide stage-only sections.
            const qcard = document.getElementById('gb-ttt-question-card');
            if (qcard) qcard.classList.remove('show');
            const rcard = document.getElementById('gb-ttt-result-card');
            if (rcard) rcard.classList.remove('show');
            const scard = document.getElementById('gb-ttt-session-card');
            if (scard) scard.classList.remove('show');
            const fbEl = document.getElementById('gb-ttt-feedback');
            if (fbEl) { fbEl.className = 'gb-ttt-feedback'; fbEl.textContent = ''; }
            gbTTTRender();
        }

        function gbTTTCellClick(idx) {
            const ttt = gbState.ttt;
            if (ttt.busy || ttt.phase !== 'await-tap') return;
            if (ttt.board[idx]) return;
            ttt.pendingCellIdx = idx;
            ttt.phase = 'awaiting-answer';
            ttt.busy = true;
            gbTTTRender();
            gbTTTShowQuestion();
        }

        function gbTTTShowQuestion() {
            const ttt = gbState.ttt;
            const item = gbTTTPickItem();
            if (!item) {
                // No items — back-out gracefully.
                ttt.phase = 'await-tap';
                ttt.busy = false;
                ttt.pendingCellIdx = -1;
                gbTTTRender();
                return;
            }
            const qcard = document.getElementById('gb-ttt-question-card');
            const qEl = document.getElementById('gb-ttt-question');
            const optsEl = document.getElementById('gb-ttt-options');
            const fbEl = document.getElementById('gb-ttt-feedback');
            if (!qcard || !qEl || !optsEl) return;
            qEl.textContent = item.q || '';
            // Server-shuffled options array — render as-is. NO client-side correct/distractors logic.
            const opts = Array.isArray(item.options) ? item.options : [];
            optsEl.innerHTML = '';
            opts.forEach((text) => {
                const b = document.createElement('button');
                b.className = 'gb-ttt-option';
                b.type = 'button';
                b.setAttribute('data-option-value', String(text));
                b.textContent = String(text);
                b.addEventListener('click', () => gbTTTOptionClick(String(text), b));
                optsEl.appendChild(b);
            });
            if (fbEl) { fbEl.className = 'gb-ttt-feedback'; fbEl.textContent = ''; }
            qcard.classList.add('show');
            setTimeout(() => {
                try { qcard.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) {}
            }, 80);
            gbTTTRender();
        }

        async function gbTTTOptionClick(picked, btnEl) {
            const ttt = gbState.ttt;
            if (ttt.busy && ttt.phase !== 'awaiting-answer') return;
            if (ttt.phase !== 'awaiting-answer') return;
            // Lock all options to prevent double-submit.
            const optsEl = document.getElementById('gb-ttt-options');
            if (optsEl) {
                Array.from(optsEl.children).forEach(c => c.setAttribute('disabled', 'disabled'));
            }
            ttt.busy = true;
            const itemId = ttt.currentItemId;
            const resp = await gbTTTCheckAnswer(itemId, picked);
            gbTTTHandleResolve(resp, btnEl, picked);
        }

        function gbTTTHandleResolve(resp, btnEl, picked) {
            const ttt = gbState.ttt;
            const fbEl = document.getElementById('gb-ttt-feedback');
            const optsEl = document.getElementById('gb-ttt-options');
            const isCorrect = !!(resp && resp.is_correct);
            const isMercy = !!(resp && resp.mercy);
            const correctValue = (resp && resp.correct_value) || null;
            // Mark the picked option green/red.
            if (btnEl) btnEl.classList.add(isCorrect ? 'correct' : 'wrong');
            // Highlight the actual correct option (only after resolve).
            if (correctValue && optsEl) {
                Array.from(optsEl.children).forEach(c => {
                    if (c.getAttribute('data-option-value') === correctValue) {
                        c.classList.add('correct');
                    }
                });
            }
            // Feedback text.
            if (fbEl) {
                fbEl.classList.remove('good', 'bad');
                if (isCorrect) {
                    fbEl.classList.add('show', 'good');
                    fbEl.textContent = RT('ttt.feedbackCorrect');
                } else if (isMercy) {
                    fbEl.classList.add('show', 'good');
                    fbEl.textContent = RT('ttt.feedbackMercy');
                } else {
                    fbEl.classList.add('show', 'bad');
                    fbEl.textContent = RT('ttt.feedbackWrong');
                }
            }
            // Decide placement.
            // - is_correct → land on intended cell (pendingCellIdx)
            // - mercy bounce → also land on intended cell (lucky)
            // - wrong + no mercy → scatter to random empty cell
            let placedAt;
            if (isCorrect || isMercy) {
                placedAt = ttt.pendingCellIdx;
                if (isCorrect) {
                    ttt.correct = (ttt.correct || 0) + 1;
                }
            } else {
                // Random empty (wrong-no-mercy scatter)
                const emptyIndices = [];
                for (let i = 0; i < 9; i++) {
                    if (!ttt.board[i]) emptyIndices.push(i);
                }
                placedAt = emptyIndices.length > 0
                    ? emptyIndices[Math.floor(Math.random() * emptyIndices.length)]
                    : ttt.pendingCellIdx;
            }
            // Defer the actual placement so user can read feedback.
            ttt.lastResolveTimer = setTimeout(() => {
                if (placedAt >= 0 && placedAt < 9 && !ttt.board[placedAt]) {
                    ttt.board[placedAt] = 'X';
                }
                ttt.pendingCellIdx = -1;
                const qcard = document.getElementById('gb-ttt-question-card');
                if (qcard) qcard.classList.remove('show');
                gbTTTRender();
                gbTTTAfterPlayerMove();
            }, 700);
        }

        function gbTTTAfterPlayerMove() {
            const ttt = gbState.ttt;
            const w = gbTTTWinner(ttt.board);
            if (w) {
                ttt.winLine = w.line;
                gbTTTRender();
                gbTTTEndGame(w.mark === 'X' ? 'win' : 'loss');
                return;
            }
            if (gbTTTBoardFull(ttt.board)) {
                gbTTTEndGame('draw');
                return;
            }
            ttt.phase = 'ai-thinking';
            gbTTTRender();
            setTimeout(() => gbTTTAIMove(), 600);
        }

        function gbTTTAIMove() {
            const ttt = gbState.ttt;
            const move = gbTTTBestMove(ttt.board.slice(), 'O');
            if (move >= 0) ttt.board[move] = 'O';
            const w = gbTTTWinner(ttt.board);
            if (w) {
                ttt.winLine = w.line;
                gbTTTRender();
                gbTTTEndGame(w.mark === 'X' ? 'win' : 'loss');
                return;
            }
            if (gbTTTBoardFull(ttt.board)) {
                gbTTTRender();
                gbTTTEndGame('draw');
                return;
            }
            ttt.phase = 'await-tap';
            ttt.busy = false;
            gbTTTRender();
        }

        function gbTTTEndGame(result) {
            const ttt = gbState.ttt;
            ttt.phase = 'game-over';
            ttt.busy = true;
            ttt.games[ttt.gameNum] = result;
            if (result === 'draw') ttt.draws++;
            else if (result === 'loss') ttt.losses++;
            // Note: 'win' counter is implicit (impossible vs optimal AI); not displayed in stat grid.
            // Result card.
            const card = document.getElementById('gb-ttt-result-card');
            const titleEl = document.getElementById('gb-ttt-result-title');
            const textEl = document.getElementById('gb-ttt-result-text');
            if (card && titleEl && textEl) {
                if (result === 'win') {
                    titleEl.textContent = RT('ttt.resultWinTitle');
                    textEl.textContent = RT('ttt.resultWinText');
                } else if (result === 'draw') {
                    titleEl.textContent = RT('ttt.resultDrawTitle');
                    textEl.textContent = RT('ttt.resultDrawText');
                } else {
                    titleEl.textContent = RT('ttt.resultLossTitle');
                    textEl.textContent = RT('ttt.resultLossText');
                }
                card.classList.add('show');
                setTimeout(() => {
                    try { card.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) {}
                }, 80);
            }
            gbTTTRender();
            const isLastGame = ttt.gameNum >= 2;
            if (isLastGame) {
                gbTTTSessionEnd();
            } else {
                gbSetButtonForTTT(RT('ttt.dockNext'));
            }
        }

        function gbTTTNextGame() {
            const ttt = gbState.ttt;
            ttt.gameNum++;
            ttt.board = Array(9).fill('');
            ttt.pendingCellIdx = -1;
            ttt.currentItemId = null;
            ttt.phase = 'await-tap';
            ttt.busy = false;
            ttt.winLine = null;
            const card = document.getElementById('gb-ttt-result-card');
            if (card) card.classList.remove('show');
            const qcard = document.getElementById('gb-ttt-question-card');
            if (qcard) qcard.classList.remove('show');
            const fbEl = document.getElementById('gb-ttt-feedback');
            if (fbEl) { fbEl.className = 'gb-ttt-feedback'; fbEl.textContent = ''; }
            gbTTTRender();
            // Reset dock button to inert.
            if (typeof btn !== 'undefined' && btn) {
                btn.classList.remove('pulse', 'state-pill');
                btn.classList.add('state-line');
                if (typeof btnText !== 'undefined' && btnText) btnText.style.opacity = '0';
            }
        }

        async function gbTTTSessionEnd() {
            const ttt = gbState.ttt;
            // Hide per-game result card; show session card.
            const rcard = document.getElementById('gb-ttt-result-card');
            if (rcard) rcard.classList.remove('show');
            const summary = await gbTTTSessionFinalize();
            const card = document.getElementById('gb-ttt-session-card');
            const titleEl = document.getElementById('gb-ttt-session-title');
            const textEl = document.getElementById('gb-ttt-session-text');
            const xpEl = document.getElementById('gb-ttt-session-xp');
            const masteryEl = document.getElementById('gb-ttt-mastery-pill');
            const duolingoEl = document.getElementById('gb-ttt-duolingo-toast');
            const sessionXp = (summary && typeof summary.session_xp === 'number') ? summary.session_xp : 0;
            const bonus = (summary && typeof summary.strong_session_bonus === 'number') ? summary.strong_session_bonus : 0;
            const masteryTier = (summary && summary.mastery_tier) || '';
            const remediation = !!(summary && summary.duolingo_remediation);
            if (titleEl && textEl) {
                if (ttt.draws >= 2) {
                    titleEl.textContent = RT('ttt.sessionStrongTitle');
                    textEl.textContent = RT('ttt.sessionStrongText');
                } else if (ttt.draws === 1) {
                    titleEl.textContent = RT('ttt.sessionSolidTitle');
                    textEl.textContent = RT('ttt.sessionSolidText');
                } else {
                    titleEl.textContent = RT('ttt.sessionFailedTitle');
                    textEl.textContent = RT('ttt.sessionFailedText');
                }
            }
            if (xpEl) xpEl.textContent = sessionXp + ' XP' + (bonus > 0 ? ' (+' + bonus + ' bonus)' : '');
            if (masteryEl) {
                masteryEl.textContent = masteryTier;
                masteryEl.style.display = masteryTier ? 'inline-block' : 'none';
            }
            if (duolingoEl) {
                if (remediation) duolingoEl.classList.add('show');
                else duolingoEl.classList.remove('show');
            }
            if (card) {
                card.classList.add('show');
                setTimeout(() => {
                    try { card.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) {}
                }, 80);
            }
            ttt.complete = true;
            if (window.__sessionLog) {
                window.__sessionLog.push({
                    phase: 'tic-tac-toe', id: 'ttt-session',
                    correct: ttt.draws + (ttt.games || []).filter(g => g === 'win').length >= 2,
                    score: sessionXp,
                    sessionId: ttt.sessionId,
                    mastery: masteryTier,
                });
            }
            gbSetButtonNext(gbIsLastGame(5) ? RT('btn.next_stage') : RT('btn.continue'));
        }

        function gbSetButtonForTTT(text) {
            if (typeof btn === 'undefined' || !btn) return;
            btn.classList.remove('pulse', 'state-line');
            btn.classList.add('state-pill');
            setBtnText(text || RT('btn.continue'));
            btn.classList.add('pulse');
        }

        function gbTTTAction() {
            const ttt = gbState.ttt;
            if (!ttt) return;
            if (ttt.complete) {
                // Game-break registry hook — DO NOT change signature.
                gbAdvanceFromGame(5, 'gb-panel-ttt');
                return;
            }
            if (ttt.phase === 'game-over') {
                gbTTTNextGame();
                return;
            }
            // 'await-tap' / 'awaiting-answer' / 'ai-thinking' — button is inert; clicks come from cells / options.
        }

        /* ───────────────── MEMORY PALACE (gb-panel-mp, sub-slot 7) ─────────────────
           Method of Loci 4-step state machine. Author content (palaces + concepts +
           imagery cues) ships in GB_MEMORY_PALACE — pedagogical hint material, NOT
           an answer key. The "answer" for the recall test is the student's own
           Step 2 placement map, server-validated in gbMPSubmitSession. NO hardcoded
           palace/concept content here. ───────────────────────────────────────── */

        function gbMPShowToast(msg, kind) {
            const t = document.getElementById('gb-mp-toast');
            if (!t) return;
            t.textContent = msg || '';
            t.classList.add('show');
            if (kind === 'error') t.setAttribute('data-kind', 'error');
            else t.removeAttribute('data-kind');
            clearTimeout(gbState.mp._toastTimer);
            gbState.mp._toastTimer = setTimeout(() => {
                t.classList.remove('show');
            }, 1800);
        }

        function gbMPRenderStaticI18n() {
            // Map static labels to i18n keys. Hero kicker + step labels.
            const setText = (id, key) => {
                const el = document.getElementById(id);
                if (el) el.textContent = RT(key);
            };
            setText('gb-mp-hero-kicker', 'mp.heroKicker');
            setText('gb-mp-accuracy-label', 'mp.accuracyLabel');
            setText('gb-mp-speed-label', 'mp.speedLabel');
            setText('gb-mp-level-label', 'mp.levelLabel');
            setText('gb-mp-xp-label', 'mp.xpLabel');
            setText('gb-mp-step1-label', 'mp.step1Label');
            setText('gb-mp-step2-label', 'mp.step2Label');
            setText('gb-mp-step4-label', 'mp.step4Label');
            const retry = document.getElementById('gb-mp-retry-btn');
            if (retry) retry.textContent = RT('mp.dockRetry');
        }

        function gbInitMP() {
            // Reset state. Only run when GB_MEMORY_PALACE is non-null and has palaces+concepts.
            const wire = (typeof GB_MEMORY_PALACE === 'object' && GB_MEMORY_PALACE) ? GB_MEMORY_PALACE : null;
            const palaces = (wire && Array.isArray(wire.palaces)) ? wire.palaces.slice() : [];
            const concepts = (wire && Array.isArray(wire.concepts)) ? wire.concepts.slice() : [];
            const ctx = window.NETS_CTX || {};
            const isPremium = (ctx.tier === 'premium');
            // Tier filter — keep premium palaces only when student tier is premium.
            const filtered = palaces.filter(p => {
                if (!p || typeof p !== 'object') return false;
                const ptier = (p.tier || 'basic').toLowerCase();
                return (ptier !== 'premium') || isPremium;
            });
            const sessionId = 'mp-' + Date.now() + '-' + Math.floor(Math.random() * 9999);
            gbState.mp = Object.assign(gbState.mp || {}, {
                step: 1,
                selectedPalace: null,
                filteredPalaces: filtered,
                conceptIndex: 0,
                placements: [],
                walkIndex: 0,
                recallIndex: 0,
                recallResults: [],
                recallStartAt: null,
                recallOptions: [],
                hintsUsed: 0,
                result: null,
                sessionId: sessionId,
                busy: false,
                complete: false,
            });
            gbMPRenderStaticI18n();
            gbMPRenderStep(1);
            gbMPRenderPalaceGrid();
            // Update XP pill cosmetic baseline.
            const xpPill = document.getElementById('gb-mp-xp-pill');
            if (xpPill) xpPill.textContent = '0 XP';
            // Result card hidden + retry hidden on init.
            const result = document.getElementById('gb-mp-result-card');
            if (result) { result.classList.remove('show', 'outcome-perfect', 'outcome-yaxshi', 'outcome-hali_emas_partial', 'outcome-hali_emas_fail'); }
            const retry = document.getElementById('gb-mp-retry-btn');
            if (retry) {
                retry.classList.remove('show');
                retry.onclick = gbMPRetry;
            }
        }

        function gbMPRenderStep(step) {
            gbState.mp.step = step;
            // Toggle .active among the 4 step sections.
            for (let i = 1; i <= 4; i++) {
                const el = document.getElementById('gb-mp-step-' + i);
                if (el) el.classList.toggle('active', i === step);
            }
            // Topbar dots
            const dots = document.querySelectorAll('#gb-mp-dots span');
            dots.forEach((d, i) => d.classList.toggle('active', i === (step - 1)));
            // Step counter
            const stepLabel = document.getElementById('gb-mp-step-label');
            if (stepLabel) stepLabel.textContent = step + '/4';
            // Phase label + hero copy via i18n keys.
            const phaseKeyByStep = { 1: 'mp.step1Label', 2: 'mp.step2Label', 3: 'mp.step3Label', 4: 'mp.step4Label' };
            const titleKeyByStep = { 1: 'mp.heroTitleStep1', 2: 'mp.heroTitleStep2', 3: 'mp.heroTitleStep3', 4: 'mp.heroTitleStep4' };
            const subKeyByStep   = { 1: 'mp.heroSubStep1',   2: 'mp.heroSubStep2',   3: 'mp.heroSubStep3',   4: 'mp.heroSubStep4'   };
            const phaseEl = document.getElementById('gb-mp-phase-label');
            const titleEl = document.getElementById('gb-mp-hero-title');
            const subEl   = document.getElementById('gb-mp-hero-sub');
            if (phaseEl) phaseEl.textContent = RT(phaseKeyByStep[step] || 'mp.step1Label');
            if (titleEl) titleEl.textContent = RT(titleKeyByStep[step] || 'mp.heroTitleStep1');
            if (subEl)   subEl.textContent   = RT(subKeyByStep[step]   || 'mp.heroSubStep1');
            // Update dock label (uses global #gb-action-btn via setBtnText helper if available).
            const dockKeyByStep = { 1: 'mp.dockChoosePalace', 2: 'mp.dockPlaceConcept', 3: 'mp.dockNextStop', 4: 'mp.dockAnswerRecall' };
            const dockKey = dockKeyByStep[step] || 'mp.dockChoosePalace';
            if (typeof btn !== 'undefined' && btn) {
                btn.classList.remove('pulse');
                btn.classList.add('state-pill');
                if (typeof btnText !== 'undefined' && btnText) {
                    btnText.textContent = RT(dockKey);
                    btnText.style.opacity = '1';
                }
            }
        }

        function gbMPRenderPalaceGrid() {
            const grid = document.getElementById('gb-mp-palace-grid');
            if (!grid) return;
            grid.innerHTML = '';
            const palaces = gbState.mp.filteredPalaces || [];
            palaces.forEach(p => {
                const card = document.createElement('button');
                card.type = 'button';
                card.className = 'gb-mp-palace-card';
                if (gbState.mp.selectedPalace && gbState.mp.selectedPalace.key === p.key) {
                    card.classList.add('selected');
                }
                const icon = document.createElement('div');
                icon.className = 'gb-mp-icon';
                icon.textContent = p.icon || '🏛️';
                const title = document.createElement('strong');
                title.textContent = p.name || '';
                const desc = document.createElement('span');
                desc.textContent = p.description || '';
                card.appendChild(icon);
                card.appendChild(title);
                card.appendChild(desc);
                card.onclick = () => gbMPSelectPalace(p.key, card);
                grid.appendChild(card);
            });
        }

        function gbMPSelectPalace(palaceKey, btnEl) {
            const palace = (gbState.mp.filteredPalaces || []).find(p => p && p.key === palaceKey);
            if (!palace) return;
            gbState.mp.selectedPalace = palace;
            // Re-render to update .selected highlight.
            gbMPRenderPalaceGrid();
            // Update dock label to invite next step.
            if (typeof btnText !== 'undefined' && btnText) {
                btnText.textContent = RT('mp.dockPlaceConcept');
            }
        }

        function gbMPStartPlacement() {
            const palace = gbState.mp.selectedPalace;
            const wire = (typeof GB_MEMORY_PALACE === 'object' && GB_MEMORY_PALACE) ? GB_MEMORY_PALACE : null;
            if (!palace || !wire) return;
            const locCount = (palace.locations || []).length;
            gbState.mp.conceptIndex = 0;
            gbState.mp.placements = new Array(locCount).fill(null);
            gbMPRenderStep(2);
            gbMPRenderFocusCard();
            gbMPRenderLocationGrid();
        }

        function gbMPRenderFocusCard() {
            const wire = GB_MEMORY_PALACE;
            const concepts = (wire && wire.concepts) ? wire.concepts : [];
            const idx = gbState.mp.conceptIndex || 0;
            const c = concepts[idx];
            if (!c) return;
            const titleEl = document.getElementById('gb-mp-focus-title');
            const copyEl  = document.getElementById('gb-mp-focus-copy');
            const cueEl   = document.getElementById('gb-mp-focus-image-cue');
            const counter = document.getElementById('gb-mp-concept-counter');
            const kicker  = document.getElementById('gb-mp-focus-kicker');
            if (titleEl) titleEl.textContent = c.term || '';
            if (copyEl)  copyEl.textContent  = c.description || '';
            if (cueEl)   cueEl.textContent   = c.image_cue || '';
            if (kicker)  kicker.textContent  = RT('mp.heroKicker');
            if (counter) {
                const tmpl = RT('mp.conceptCounter');
                counter.textContent = (tmpl || 'Concept {n}/{total}')
                    .replace('{n}', String(idx + 1))
                    .replace('{total}', String(concepts.length));
            }
        }

        function gbMPRenderLocationGrid() {
            const grid = document.getElementById('gb-mp-location-grid');
            if (!grid) return;
            grid.innerHTML = '';
            const palace = gbState.mp.selectedPalace;
            if (!palace) return;
            const wire = GB_MEMORY_PALACE;
            const concepts = (wire && wire.concepts) ? wire.concepts : [];
            const locations = palace.locations || [];
            locations.forEach((loc, i) => {
                const placement = gbState.mp.placements[i];
                const card = document.createElement('button');
                card.type = 'button';
                card.className = 'gb-mp-location-card';
                if (placement) card.classList.add('occupied');
                const icon = document.createElement('div');
                icon.className = 'gb-mp-icon';
                icon.textContent = String(i + 1);
                const name = document.createElement('strong');
                name.textContent = loc.name || '';
                const sub = document.createElement('span');
                if (placement) {
                    const placedConcept = concepts.find(c => c && c.id === placement.concept_id);
                    const term = placedConcept ? placedConcept.term : '';
                    const tmpl = RT('mp.placementOccupied') || 'Holding: {term}';
                    sub.textContent = tmpl.replace('{term}', term);
                } else {
                    sub.textContent = loc.sensory_cue || '';
                }
                card.appendChild(icon);
                card.appendChild(name);
                card.appendChild(sub);
                if (!placement) {
                    card.onclick = () => gbMPPlace(i, card);
                } else {
                    card.disabled = true;
                }
                grid.appendChild(card);
            });
        }

        function gbMPPlace(locationIdx, btnEl) {
            const wire = GB_MEMORY_PALACE;
            const concepts = (wire && wire.concepts) ? wire.concepts : [];
            const ci = gbState.mp.conceptIndex || 0;
            const concept = concepts[ci];
            if (!concept) return;
            if (gbState.mp.placements[locationIdx]) {
                gbMPShowToast(RT('mp.placementOccupied').replace('{term}', ''));
                return;
            }
            gbState.mp.placements[locationIdx] = {
                location_idx: locationIdx,
                concept_id: concept.id,
            };
            gbState.mp.conceptIndex = ci + 1;
            if (gbState.mp.conceptIndex >= concepts.length) {
                // All concepts placed — advance to walk.
                gbMPRenderLocationGrid();
                setTimeout(() => gbMPStartWalk(), 380);
                return;
            }
            gbMPRenderFocusCard();
            gbMPRenderLocationGrid();
        }

        function gbMPStartWalk() {
            gbState.mp.walkIndex = 0;
            gbMPRenderStep(3);
            gbMPRenderWalkCard();
        }

        function gbMPRenderWalkCard() {
            const palace = gbState.mp.selectedPalace;
            if (!palace) return;
            const wire = GB_MEMORY_PALACE;
            const concepts = (wire && wire.concepts) ? wire.concepts : [];
            const locations = palace.locations || [];
            const idx = gbState.mp.walkIndex || 0;
            const loc = locations[idx];
            const placement = gbState.mp.placements[idx];
            const placedConcept = placement ? concepts.find(c => c && c.id === placement.concept_id) : null;
            const iconEl  = document.getElementById('gb-mp-walk-icon');
            const titleEl = document.getElementById('gb-mp-walk-title');
            const copyEl  = document.getElementById('gb-mp-walk-copy');
            const counter = document.getElementById('gb-mp-walk-counter');
            if (iconEl)  iconEl.textContent  = palace.icon || '🕌';
            if (titleEl) titleEl.textContent = (loc && loc.name) || '';
            if (copyEl) {
                const term = placedConcept ? placedConcept.term : '';
                const cue  = placedConcept ? (placedConcept.image_cue || '') : '';
                const sens = (loc && loc.sensory_cue) || '';
                copyEl.textContent = (term ? term + ' — ' : '') + cue + (sens ? ' · ' + sens : '');
            }
            if (counter) {
                const tmpl = RT('mp.walkCounter') || 'Stop {n}/{total}';
                counter.textContent = tmpl.replace('{n}', String(idx + 1)).replace('{total}', String(locations.length));
            }
            // Dock label
            const isLast = (idx >= locations.length - 1);
            if (typeof btnText !== 'undefined' && btnText) {
                btnText.textContent = isLast ? RT('mp.dockAnswerRecall') : RT('mp.dockNextStop');
            }
        }

        function gbMPAdvanceWalk() {
            const palace = gbState.mp.selectedPalace;
            if (!palace) return;
            const locations = palace.locations || [];
            gbState.mp.walkIndex = (gbState.mp.walkIndex || 0) + 1;
            if (gbState.mp.walkIndex >= locations.length) {
                gbMPStartRecall();
                return;
            }
            gbMPRenderWalkCard();
        }

        function gbMPStartRecall() {
            gbState.mp.recallIndex = 0;
            gbState.mp.recallResults = [];
            gbState.mp.recallStartAt = Date.now();
            gbMPRenderStep(4);
            gbMPRenderRecall();
        }

        function gbMPRenderRecall() {
            const palace = gbState.mp.selectedPalace;
            if (!palace) return;
            const wire = GB_MEMORY_PALACE;
            const concepts = (wire && wire.concepts) ? wire.concepts : [];
            const idx = gbState.mp.recallIndex || 0;
            const loc = (palace.locations || [])[idx];
            const placement = gbState.mp.placements[idx];
            const correctConcept = placement ? concepts.find(c => c && c.id === placement.concept_id) : null;
            const locEl  = document.getElementById('gb-mp-recall-location');
            const qEl    = document.getElementById('gb-mp-recall-question');
            const opts   = document.getElementById('gb-mp-recall-options');
            const counter = document.getElementById('gb-mp-recall-counter');
            if (locEl) locEl.textContent = (loc && loc.name) || '';
            if (qEl)   qEl.textContent   = RT('mp.recallQuestion');
            if (counter) {
                const tmpl = RT('mp.recallCounter') || 'Question {n}/{total}';
                counter.textContent = tmpl.replace('{n}', String(idx + 1)).replace('{total}', String((palace.locations || []).length));
            }
            // Build 4 MC options: 1 correct + 3 distractors. NEVER reveal correctness in DOM
            // until user picks (only via button.onclick comparison post-pick).
            if (!opts) return;
            opts.innerHTML = '';
            if (!correctConcept) return;
            const distractors = concepts
                .filter(c => c && c.id !== correctConcept.id)
                .slice();
            // Fisher-Yates shuffle distractors (avoid fixed ordering exposing answer).
            for (let i = distractors.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                const t = distractors[i]; distractors[i] = distractors[j]; distractors[j] = t;
            }
            const picks = [correctConcept].concat(distractors.slice(0, 3));
            for (let i = picks.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                const t = picks[i]; picks[i] = picks[j]; picks[j] = t;
            }
            gbState.mp.recallOptions = picks.map(p => p.id);
            gbState.mp.recallStartAt = Date.now();
            picks.forEach(opt => {
                const btnEl = document.createElement('button');
                btnEl.type = 'button';
                btnEl.className = 'gb-mp-recall-option';
                btnEl.setAttribute('data-concept-id', opt.id);
                const term = document.createElement('strong');
                term.textContent = opt.term || '';
                btnEl.appendChild(term);
                btnEl.onclick = () => gbMPAnswerRecall(opt.id, btnEl);
                opts.appendChild(btnEl);
            });
        }

        function gbMPAnswerRecall(pickedConceptId, btnEl) {
            const palace = gbState.mp.selectedPalace;
            if (!palace) return;
            const idx = gbState.mp.recallIndex || 0;
            const placement = gbState.mp.placements[idx];
            const expectedId = placement ? placement.concept_id : null;
            // Client-side `is_correct` is informational only — server recomputes
            // authoritatively from the submitted placement map in gbMPSubmitSession.
            const isCorrect = (pickedConceptId === expectedId) && (pickedConceptId !== null);
            const elapsedMs = Math.max(0, Date.now() - (gbState.mp.recallStartAt || Date.now()));
            // Disable all options + visual feedback (correct/wrong).
            const opts = document.getElementById('gb-mp-recall-options');
            if (opts) {
                Array.from(opts.children).forEach(child => {
                    child.disabled = true;
                    const cid = child.getAttribute('data-concept-id');
                    if (cid === expectedId) child.classList.add('correct');
                });
                if (!isCorrect && btnEl) btnEl.classList.add('wrong');
            }
            gbState.mp.recallResults.push({
                location_idx: idx,
                picked_concept_id: pickedConceptId,
                is_correct: isCorrect,
                elapsed_ms: elapsedMs,
            });
            // Advance after brief pause.
            setTimeout(() => {
                gbState.mp.recallIndex = idx + 1;
                const total = (palace.locations || []).length;
                if (gbState.mp.recallIndex >= total) {
                    gbMPSubmitSession();
                } else {
                    gbMPRenderRecall();
                }
            }, 700);
        }

        // Single network swap-point. Reads ctx.hwId FIRST per TM #140 / SF / TTT lesson,
        // then snake_case alternates (homework_id, homeworkId). Fail-soft on any HTTP /
        // network error: render a locally-computed approximate result + show toast.
        async function gbMPSubmitSession() {
            const ctx = window.NETS_CTX || {};
            const homeworkId = ctx.hwId || ctx.homework_id || ctx.homeworkId || null;
            const palace = gbState.mp.selectedPalace;
            const palaceKey = palace ? palace.key : null;
            const placements = (gbState.mp.placements || []).filter(p => p && typeof p.location_idx !== 'undefined');
            const recallResults = gbState.mp.recallResults || [];
            const hintsUsed = gbState.mp.hintsUsed || 0;
            // Local fallback outcome computation for fail-soft only.
            const localCorrect = recallResults.filter(r => r && r.is_correct).length;
            const localTotal = recallResults.length || 1;
            const fallback = {
                outcome: localCorrect === localTotal ? 'perfect' : (localCorrect >= localTotal - 1 ? 'yaxshi' : (localCorrect >= Math.ceil(localTotal * 0.6) ? 'hali_emas_partial' : 'hali_emas_fail')),
                outcome_title: '',
                outcome_text: '',
                accuracy_pct: Math.round((localCorrect / localTotal) * 100),
                correct_count: localCorrect,
                total_count: localTotal,
                recall_speed_avg_s: 0,
                level_label: 'pending',
                session_xp_display: localCorrect * 50,
                retry_offered: localCorrect < localTotal,
                missed_location_indices: recallResults.filter(r => r && !r.is_correct).map(r => r.location_idx),
            };
            if (!homeworkId) {
                gbMPShowToast(RT('mp.toastNetwork'), 'error');
                gbMPRenderResult(fallback);
                return;
            }
            try {
                const res = await fetch('/api/ai/check-answer?phase=memory-palace', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        phase: 'memory-palace',
                        homework_id: homeworkId,
                        palace_key: palaceKey,
                        placements: placements,
                        recall_results: recallResults,
                        hints_used: hintsUsed,
                    }),
                });
                if (!res.ok) {
                    gbMPShowToast(RT('mp.toastNetwork'), 'error');
                    gbMPRenderResult(fallback);
                    return;
                }
                const resp = await res.json();
                gbState.mp.result = resp;
                gbMPRenderResult(resp);
            } catch (err) {
                gbMPShowToast(RT('mp.toastNetwork'), 'error');
                gbMPRenderResult(fallback);
            }
        }

        function gbMPRenderResult(resp) {
            // Server-authoritative — read outcome / accuracy / xp / level from response.
            // Locally-computed fallback only on network failure (handled in gbMPSubmitSession).
            if (!resp) return;
            const card = document.getElementById('gb-mp-result-card');
            const title = document.getElementById('gb-mp-result-title');
            const text  = document.getElementById('gb-mp-result-text');
            const acc   = document.getElementById('gb-mp-accuracy-value');
            const speed = document.getElementById('gb-mp-speed-value');
            const lvl   = document.getElementById('gb-mp-level-value');
            const xp    = document.getElementById('gb-mp-xp-value');
            const xpPill = document.getElementById('gb-mp-xp-pill');
            const retry = document.getElementById('gb-mp-retry-btn');
            const outcome = resp.outcome || 'hali_emas_partial';
            if (title) {
                const localTitle = RT('mp.outcome.' + outcome);
                title.textContent = localTitle && localTitle !== ('mp.outcome.' + outcome)
                    ? localTitle
                    : (resp.outcome_title || '');
            }
            if (text) text.textContent = resp.outcome_text || '';
            if (acc)  acc.textContent  = (resp.accuracy_pct != null ? resp.accuracy_pct : 0) + '%';
            if (speed) speed.textContent = (resp.recall_speed_avg_s != null ? resp.recall_speed_avg_s : 0) + 's';
            if (lvl) {
                // Try i18n translation of level_label first; fall back to raw string.
                const lvlKey = resp.level_label || 'pending';
                const tx = RT('mp.level.' + String(lvlKey).toLowerCase().replace(/[^a-z0-9]/g, '_'));
                lvl.textContent = (tx && tx.indexOf('mp.level.') === -1) ? tx : (resp.level_label || RT('mp.level.pending'));
            }
            const xpVal = (resp.session_xp_display != null) ? resp.session_xp_display : 0;
            // session_xp_display is COSMETIC-ONLY (plan §1.3 + §7 #9). Show on card +
            // top-right XP pill. DO NOT write to window.__sessionLog or any persistent counter.
            if (xp) xp.textContent = xpVal + ' XP';
            if (xpPill) xpPill.textContent = xpVal + ' XP';
            if (card) {
                card.classList.add('show');
                card.classList.remove('outcome-perfect', 'outcome-yaxshi', 'outcome-hali_emas_partial', 'outcome-hali_emas_fail');
                card.classList.add('outcome-' + outcome);
            }
            if (retry) {
                if (resp.retry_offered) retry.classList.add('show');
                else retry.classList.remove('show');
                retry.textContent = RT('mp.dockRetry');
                retry.onclick = gbMPRetry;
            }
            gbState.mp.complete = true;
            // Update dock label.
            if (typeof btnText !== 'undefined' && btnText) {
                btnText.textContent = RT('mp.dockComplete');
            }
        }

        function gbMPAction() {
            const mp = gbState.mp;
            if (!mp) return;
            if (mp.complete) {
                // Game-break registry hook — DO NOT change signature.
                gbAdvanceFromGame(7, 'gb-panel-mp');
                return;
            }
            if (mp.busy) return;
            if (mp.step === 1) {
                if (!mp.selectedPalace) {
                    gbMPShowToast(RT('mp.dockChoosePalace'));
                    return;
                }
                gbMPStartPlacement();
                return;
            }
            if (mp.step === 2) {
                // Step 2 auto-advances on location click; dock is informational.
                gbMPShowToast(RT('mp.dockPlaceConcept'));
                return;
            }
            if (mp.step === 3) {
                gbMPAdvanceWalk();
                return;
            }
            if (mp.step === 4) {
                // Step 4 auto-advances on option pick; dock no-ops.
                return;
            }
        }

        function gbMPRetry() {
            // Restart from Step 1 — clear placements + recall but keep sessionId
            // so the server can correlate retry attempts (future mastery feature).
            const sid = (gbState.mp && gbState.mp.sessionId) || null;
            gbInitMP();
            if (sid) gbState.mp.sessionId = sid;
        }

        function gbExitToStage6() {
            if (state.isAnimating) return;
            state.isAnimating = true;
            // Game Breaks phase done — student cleared (or skipped past) all
            // sub-games. Reading interstitial counts under this dot too.
            completePhase('gameBreaks');
            // Clear `tm-dock-hidden` here: Tile Match's dock prompts add that
            // class (CSS rule `opacity: 0 !important`) to suppress the morph
            // button while tile prompts are active. Normal flow auto-clears
            // it via gbSetButtonNext when advancing to the next sub-game,
            // but the exit path (last GB sub-game → startStage6) doesn't
            // route through that helper, so without this explicit removal
            // the next phase (Real Life) inherits an invisible action button.
            btn.classList.remove('pulse','state-pill','tm-dock-hidden');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            const s5 = document.getElementById('screen-5');
            if (s5) { s5.style.transition = 'opacity 400ms ease'; s5.style.opacity = '0'; }
            setTimeout(() => {
                if (s5) { s5.classList.remove('active'); s5.style.opacity = ''; s5.style.transition = ''; }
                setStage(6);
                state.isAnimating = false;
                if (RLC_CASE && typeof startRLCStage6 === 'function') {
                    startRLCStage6();
                } else if (typeof startStage6 === 'function') {
                    startStage6();
                } else {
                    const app = document.getElementById('app');
                    const placeholder = document.createElement('div');
                    placeholder.style.cssText = 'position:absolute;width:100%;height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:32px;';
                    placeholder.innerHTML = "<h2 style='color:var(--accent)'>" + RT('gb.break_done') + "</h2><p style='margin-top:12px;color:var(--text-muted)'>Next phase pending \u2014 Stage 6 loads here.</p>";
                    app.appendChild(placeholder);
                }
            }, 450);
        }

        window.addEventListener('DOMContentLoaded', init);

        /* ── STAGE 6 · REAL-LIFE CHALLENGE ─────────────────────────────── */

        const RL_SCENARIO = {
            title: 'Yashil Makon loyihasi · Toshkent ekologik zonasi',
            story: `Prezidentimiz Shavkat Miromonovich Mirziyoyev tomonidan imzolangan "Yashil Makon" davlat dasturi doirasida Toshkent viloyatida yangi ekologik dam olish zonasi barpo etilmoqda. Siz bu strategik loyihaning biznes-proyekt menedjeri sifatida tayinlandingiz.

Sizning vazifangiz — hududning aniq chegaralarini hisoblash, byudjetni boshqarish va Prezident Administratsiyasiga aniq hisobot topshirish.

Berilgan ma'lumotlar:
• Ajratilgan byudjet: 43 200 000 so'm
• Tuproq va daraxt o'rnatish narxi: 1 m² uchun 1 000 so'm
• Hudud to'rtburchak shaklida (shahar arxitektura byurosi qarori)
• Uzunligi kengligidan 60 metr ortiq (suv kanali va favqulodda xizmatlar uchun)
• Byudjet to'liq sarflanishi kerak — bir m² ham qoldirib bo'lmaydi

Prezident ertaga hisobot kutmoqda.`,
            questions: [
                {
                    id: 'Q1', type: 'text', bloom: 'L3', pisa: 'P2', capture: false,
                    prompt: 'Hudud kengligini x (metr) deb oling. Uzunlikni va umumiy maydonni x orqali ifodalang. Byudjet shartidan tenglama tuzing.',
                    acceptableAnswers: ['x(x + 60) = 43200', 'x(x+60)=43200', 'x² + 60x = 43200', 'x^2 + 60x = 43200'],
                    hint: 'Maslahat: Maydon × 1000 so\'m = 43 200 000. Maydonni x orqali yozing.'
                },
                {
                    id: 'Q2', type: 'multi-input', bloom: 'L2', pisa: 'P2', capture: false,
                    prompt: 'Tenglamani standart shaklga keltiring. a, b, c koeffitsiyentlarini aniqlang.',
                    fields: [
                        { label: 'Standart shakl', acceptable: ['x² + 60x - 43200 = 0', 'x²+60x-43200=0', 'x^2 + 60x - 43200 = 0'] },
                        { label: 'a', acceptable: ['1'] },
                        { label: 'b', acceptable: ['60'] },
                        { label: 'c', acceptable: ['-43200', '–43200'] }
                    ]
                },
                {
                    id: 'Q3', type: 'text-with-capture', bloom: 'L4', pisa: 'P3', capture: true,
                    prompt: 'Ko\'paytuvchilarga ajratish usuli bilan tenglamani yeching. (p + q = b, p · q = c)',
                    acceptableAnswers: ['180 va -240', '180, -240', 'x=180, x=-240', '180 yoki -240', '180 va –240', 'x = 180'],
                    expectedWork: 'p+q=60, pq=-43200 → (-180, 240); (x-180)(x+240)=0; x=180 yoki x=-240'
                },
                {
                    id: 'Q4', type: 'text', bloom: 'L4', pisa: 'P3', capture: false,
                    prompt: 'Menejer sifatida qaysi javobni tanlaysiz? Ikkinchi javob nega rad etiladi?',
                    acceptableAnswers: ['180', 'x = 180', 'kenglik 180', '180 metr'],
                    hint: 'Maslahat: Hudud kengligi manfiy bo\'lishi mumkinmi?'
                },
                {
                    id: 'Q5', type: 'multi-input', bloom: 'L3', pisa: 'P2', capture: false,
                    prompt: 'Prezident Administratsiyasi uchun hisobot to\'ldiring:',
                    fields: [
                        { label: 'Kenglik (m)', acceptable: ['180'] },
                        { label: 'Uzunlik (m)', acceptable: ['240'] },
                        { label: 'Maydon (m²)', acceptable: ['43200', '43 200'] },
                        { label: 'Xarajat (so\'m)', acceptable: ['43200000', '43 200 000'] }
                    ]
                },
                {
                    id: 'Q6', type: 'textarea', bloom: 'L5', pisa: 'P4', capture: false,
                    prompt: 'Agar Prezident Administratsiyasi "uzunlik kenglikdan atigi 40 metr ortiq bo\'lsin" desa, byudjet qanday o\'zgartirilishi kerak? Qisqa tahlil yozing.',
                    accepted: 'open-ended'
                }
            ],
            closure: {
                title: 'Loyiha tugadi ✓',
                message: 'Siz Yashil Makon zonasining aniq o\'lchamlarini aniqladingiz va Prezident Administratsiyasiga hisobot topshirishga tayyorsiz.'
            }
        };

        const RLC_CASE = __RLC_CASE__;

        const stage6State = {
            screen: 'story',
            qIndex: 0,
            attempts: [0, 0, 0, 0, 0, 0],
            correct: [false, false, false, false, false, false],
            // Per-question capture flag — one slot per question. The old
            // single-boolean captureQ3Done blocked submissions on every
            // text-with-capture question after Q3 since only the Q3 button
            // could set it. Kept the legacy field for back-compat reads.
            captureDone: [false, false, false, false, false, false],
            captureQ3Done: false,
            submitted: [false, false, false, false, false, false],
            captureCount: 0,
            // Per-question busy flag — guards against double-submit while a
            // check is in flight (local or AI). Set true on submit, false on
            // verdict / safety timeout. The submit handler returns early when
            // checking[idx] is true so the user can mash the button without
            // firing the AI twice.
            checking: [false, false, false, false, false, false],
            // Per-question hint visibility — toggled by .rl-hint-toggle. Hints
            // are opt-in only; they never auto-display so students who don't
            // need help aren't shown one (per design rule).
            hintOpen: [false, false, false, false, false, false]
        };

        function rlNorm(s) {
            return s.toLowerCase().replace(/\s+/g, ' ').replace(/[–—]/g, '-').trim();
        }

        function rlMatchText(val, list) {
            const nv = rlNorm(val);
            return list.some(a => rlNorm(a) === nv);
        }

        function rlMatchMulti(fields, fieldEls) {
            let allOk = true;
            fields.forEach((f, i) => {
                const inp = fieldEls[i];
                if (!inp) { allOk = false; return; }
                if (!rlMatchText(inp.value, f.acceptable)) allOk = false;
            });
            return allOk;
        }

        function rlCapture(idx) {
            // Per-question capture handler — replaces the legacy
            // rlCaptureQ3 single-button flow. Marks captureDone[idx] so
            // rlSubmitQuestion's "uploaded?" gate passes for THAT question
            // (the gate used to be a single boolean → all text-with-capture
            // questions other than Q3 were un-submittable).
            if (!stage6State.captureDone) stage6State.captureDone = [];
            stage6State.captureDone[idx] = true;
            stage6State.captureCount++;
            // Legacy alias kept so anything still reading captureQ3Done
            // behaves the same once any capture happens.
            stage6State.captureQ3Done = true;
            const btn = document.getElementById('rl-q' + (idx + 1) + '-capture-btn');
            const done = document.getElementById('rl-q' + (idx + 1) + '-capture-done');
            if (btn) btn.style.display = 'none';
            if (done) {
                done.classList.add('rl-visible');
                done.classList.add('show');
            }
        }

        // Legacy alias for the hardcoded Q3 button still in the markup.
        function rlCaptureQ3() { rlCapture(2); }

        // Structured feedback renderer. Emits:
        //   <div class="rl-feedback-main">
        //     <span class="rl-verdict ...">✓ To'g'ri | ✗ Noto'g'ri | spinner</span>
        //     <span class="rl-feedback-text">[message + optional AI baho badge]</span>
        //   </div>
        //
        // opts:
        //   aiBadge:   bool — append <span class="screen-reading-ai-badge">AI baho</span>
        //                     to the text (only fire on AI-graded results)
        //   showTutor: bool — DEPRECATED. Kept for back-compat with any caller
        //                     still passing it; ignored. Tutor is now offered
        //                     via the per-question pre-submit button rather
        //                     than inline in the feedback band.
        //
        // text:
        //   may contain HTML — we trust author/translation/AI sources here
        //   the same way the rest of the runtime does (existing innerHTML
        //   sites). If we ever sanitize, do it at the data-entry boundary,
        //   not here.
        function rlSetFeedback(id, cls, text, opts) {
            const el = document.getElementById(id);
            if (!el) return;
            opts = opts || {};
            el.className = 'rl-feedback ' + cls;
            el.setAttribute('aria-live', 'polite');

            let marker = '';
            if (cls === 'rl-correct') {
                marker = '<span class="rl-verdict rl-verdict-ok">✓ To‘g‘ri</span>';
            } else if (cls === 'rl-wrong') {
                marker = '<span class="rl-verdict rl-verdict-bad">✗ Noto‘g‘ri</span>';
            } else if (cls === 'rl-loading') {
                marker = '<span class="rl-spinner" aria-hidden="true"></span>'
                       + '<span class="rl-verdict rl-verdict-checking">Tekshirilmoqda…</span>';
            }
            // rl-hint and rl-open render no verdict pill — they are
            // pre-AI states (local hint / acknowledged open response)
            // not verdicts.

            const badge = (opts.aiBadge === true)
                ? ' <span class="screen-reading-ai-badge">AI baho</span>'
                : '';

            el.innerHTML =
                '<div class="rl-feedback-main">'
              +   marker
              +   '<span class="rl-feedback-text">' + (text || '') + badge + '</span>'
              + '</div>';
        }

        function rlHideFeedback(id) {
            const el = document.getElementById(id);
            if (el) { el.className = 'rl-feedback'; el.innerHTML = ''; }
        }

        // Toggle the per-question hint panel. Hints are opt-in — they never
        // auto-display on first wrong attempt anymore (per design rule).
        // The button label flips between "Show hint" and "Hide hint" so the
        // affordance is obvious in both states.
        function rlToggleHint(idx) {
            const panel = document.getElementById('rl-q' + (idx + 1) + '-hint-panel');
            const btn = document.getElementById('rl-q' + (idx + 1) + '-hint-toggle');
            if (!panel) return;
            const open = !panel.hidden;
            panel.hidden = open; // flip
            if (stage6State.hintOpen) stage6State.hintOpen[idx] = !open;
            if (btn) {
                btn.setAttribute('aria-expanded', open ? 'false' : 'true');
                btn.textContent = open ? RT('btn.show_hint') : RT('btn.hide_hint');
            }
        }

        // Open the persistent tutor widget. The student must be able to ask
        // the tutor BEFORE they submit (they don't get a retry afterward).
        // Programmatically clicks the floating CTA so we don't duplicate
        // its show-panel logic here.
        function rlAskTutor(idx) {
            // Mark this question's tutor was offered — could be used for
            // analytics / session log; for now just opens the panel.
            const cta = document.getElementById('nets-tutor-cta');
            if (cta) {
                cta.removeAttribute('hidden');
                cta.click();
            } else {
                // Fall back to dispatching the open event directly — covers
                // the case where the CTA is suppressed but the widget is
                // still mounted.
                try {
                    document.dispatchEvent(new CustomEvent('nets:tutor:open', { detail: { phase: 'real-life', qIndex: idx } }));
                } catch (e) {}
            }
        }

        function rlRenderStory() {
            const scroll = document.getElementById('rl-story-scroll');
            const dots = document.getElementById('rl-story-dots');
            if (scroll) {
                scroll.innerHTML = '';
                const story = RL_SCENARIO.story || '';
                // Split on blank-line paragraph breaks; fall back to a single
                // chunk if author wrote one continuous block.
                const chunks = story.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean);
                const paragraphs = chunks.length ? chunks : [story];

                // Pack content into pages two-stage:
                // 1) try paragraph-at-a-time; if a paragraph would overflow,
                //    roll back and start a new page with that paragraph
                // 2) if a single paragraph is itself bigger than the panel,
                //    split it into sentences and pack those into pages so the
                //    text never gets clipped at the bottom edge.
                const panelHeight = scroll.clientHeight || 220;
                let pageEl = null;
                let pageTextEl = null;
                const startNewPage = () => {
                    pageEl = document.createElement('div');
                    pageEl.className = 'rl-story-page';
                    pageTextEl = document.createElement('p');
                    pageTextEl.className = 'rl-story-text';
                    pageEl.appendChild(pageTextEl);
                    scroll.appendChild(pageEl);
                };
                // Split a too-tall paragraph into sentence-level chunks. We
                // keep terminators with the sentence so the text reads
                // naturally. Falls through to whole-paragraph if no
                // sentence boundaries exist.
                const sentenceSplit = (text) => {
                    const out = [];
                    const re = /[^.!?\n]+[.!?\n]+\s*|[^.!?\n]+$/g;
                    let m;
                    while ((m = re.exec(text)) !== null) {
                        const piece = m[0].trim();
                        if (piece) out.push(piece);
                    }
                    return out.length ? out : [text];
                };
                const appendChunk = (chunk, sep) => {
                    const prev = pageTextEl.innerHTML;
                    pageTextEl.innerHTML = prev + (prev ? sep : '') + chunk;
                    if (pageTextEl.scrollHeight > panelHeight && prev) {
                        // Overflow with content already on the page → roll
                        // back, start a new page, and place this chunk alone.
                        pageTextEl.innerHTML = prev;
                        startNewPage();
                        pageTextEl.innerHTML = chunk;
                    }
                };
                startNewPage();
                paragraphs.forEach((para) => {
                    // Try the whole paragraph first.
                    const probePrev = pageTextEl.innerHTML;
                    pageTextEl.innerHTML = probePrev + (probePrev ? '\n\n' : '') + para;
                    if (pageTextEl.scrollHeight <= panelHeight) {
                        // Fits — keep as-is.
                        return;
                    }
                    // Doesn't fit. Roll back, then either start a new page
                    // (if there was prior content) or split this paragraph
                    // into sentences for sub-page packing.
                    pageTextEl.innerHTML = probePrev;
                    if (probePrev) startNewPage();
                    pageTextEl.innerHTML = para;
                    if (pageTextEl.scrollHeight <= panelHeight) {
                        // Single-paragraph page that fits when alone.
                        return;
                    }
                    // Even alone the paragraph overflows — split by sentence.
                    pageTextEl.innerHTML = '';
                    const sentences = sentenceSplit(para);
                    sentences.forEach((s) => appendChunk(s, ' '));
                });

                // Render the page-indicator dots.
                if (dots) {
                    dots.innerHTML = '';
                    const pageCount = scroll.children.length;
                    dots.setAttribute('data-pages', String(pageCount));
                    for (let i = 0; i < pageCount; i++) {
                        const d = document.createElement('span');
                        d.className = 'rl-story-dot' + (i === 0 ? ' is-active' : '');
                        d.setAttribute('data-page', String(i));
                        dots.appendChild(d);
                    }
                }

                // Update active dot on scroll. Native scroll-snap handles the
                // snap; we only listen so the dots reflect the visible page.
                if (!scroll.__rlDotsBound) {
                    scroll.__rlDotsBound = true;
                    scroll.addEventListener('scroll', () => {
                        const w = scroll.clientWidth || 1;
                        const cur = Math.round(scroll.scrollLeft / w);
                        const all = dots ? dots.querySelectorAll('.rl-story-dot') : [];
                        all.forEach((el, i) => {
                            if (i === cur) el.classList.add('is-active');
                            else el.classList.remove('is-active');
                        });
                    }, { passive: true });
                }

                // Mouse drag-to-pan for desktop. Touch is handled by native
                // overflow-x scroll. Two-stage: mousedown captures intent,
                // then we only enter "drag" mode if the user actually moves
                // past a threshold — that way a normal click (no movement)
                // still allows text selection.
                if (!scroll.__rlDragBound) {
                    scroll.__rlDragBound = true;
                    const DRAG_THRESHOLD = 6;
                    let downX = 0, downScroll = 0;
                    let pending = false;   // mousedown captured, threshold not yet crossed
                    let active = false;    // crossed threshold — actively dragging
                    let suppressNextClick = false;

                    scroll.addEventListener('mousedown', (e) => {
                        if (e.button !== 0) return;
                        // Don't intercept clicks on form controls / links inside the panel.
                        const tag = (e.target.tagName || '').toLowerCase();
                        if (tag === 'input' || tag === 'button' || tag === 'a' || tag === 'select') return;
                        pending = true;
                        active = false;
                        downX = e.clientX;
                        downScroll = scroll.scrollLeft;
                    });

                    window.addEventListener('mousemove', (e) => {
                        if (!pending) return;
                        const dx = e.clientX - downX;
                        if (!active) {
                            if (Math.abs(dx) < DRAG_THRESHOLD) return;
                            // Crossed threshold — enter drag mode. preventDefault
                            // here suppresses the in-progress text selection
                            // and the cursor flips to grabbing.
                            active = true;
                            scroll.classList.add('rl-dragging');
                            // Clear any selection that may have started before
                            // the threshold was crossed.
                            const sel = window.getSelection && window.getSelection();
                            if (sel && sel.removeAllRanges) sel.removeAllRanges();
                        }
                        e.preventDefault();
                        scroll.scrollLeft = downScroll - dx;
                    });

                    window.addEventListener('mouseup', (e) => {
                        if (!pending) return;
                        pending = false;
                        if (active) {
                            active = false;
                            scroll.classList.remove('rl-dragging');
                            // Snap to nearest page (scroll-snap usually handles
                            // this on its own, but a manual smoothScroll guards
                            // against browsers that don't snap on programmatic
                            // scrollLeft changes).
                            const w = scroll.clientWidth || 1;
                            const target = Math.round(scroll.scrollLeft / w) * w;
                            scroll.scrollTo({ left: target, behavior: 'smooth' });
                            // Swallow the synthetic click that follows mouseup
                            // so a drag-release doesn't accidentally trigger
                            // any click handler under the cursor.
                            suppressNextClick = true;
                        }
                    });

                    scroll.addEventListener('click', (e) => {
                        if (suppressNextClick) {
                            suppressNextClick = false;
                            e.preventDefault();
                            e.stopPropagation();
                        }
                    }, true);
                }

                // Keyboard navigation — ←/→ flips story pages when the RL
                // screen is active. Document-level listener (idempotent
                // via __rlKeyboardBound guard) so the student can press
                // arrows without focusing the panel first.
                if (!document.__rlKeyboardBound) {
                    document.__rlKeyboardBound = true;
                    document.addEventListener('keydown', (e) => {
                        const screen = document.getElementById('screen-6');
                        const sc = document.getElementById('rl-story-scroll');
                        if (!screen || !screen.classList.contains('active') || !sc) return;
                        if (e.key === 'ArrowRight') {
                            sc.scrollBy({ left: sc.clientWidth, behavior: 'smooth' });
                        } else if (e.key === 'ArrowLeft') {
                            sc.scrollBy({ left: -sc.clientWidth, behavior: 'smooth' });
                        }
                    });
                }
            }
            const badge = document.getElementById('rl-header-badge');
            if (badge) badge.textContent = RT('rl.task_badge') + ' · ' + (RL_SCENARIO.title || RL_SCENARIO.badge || '');
            // Story view has no active question, so the per-question
            // Bloom/PISA tags don't apply — clear the meta slot so it
            // hides via :empty.
            const metaEl = document.getElementById('rl-q-header-meta');
            if (metaEl) metaEl.textContent = '';
        }

        // Extract `[Bloom: LX | PISA: LY]` tags from a prompt string. Tags
        // are author-supplied as a suffix inside q.prompt; we surface them
        // in the top-right header slot instead of leaving them inline at
        // the end of the question text. Returns {tags, stripped} where
        // tags is a display-ready string (or '' if no match) and stripped
        // is q.prompt with the tag substring removed. Permissive regex
        // covers the variants seen in production: with/without colons,
        // with/without L/P prefix, "|" or "·" or "," separator, mixed case.
        //
        // Order assumption: Bloom appears BEFORE PISA in the bracket.
        // Production data uses this order universally; reversed order
        // (e.g. `[PISA: L2 | Bloom: L3]`) is not supported and the tags
        // will remain inline. If this needs to change, swap to two
        // alternation branches inside the regex — but verify against
        // actual production data first; adding flexibility blindly
        // doubles the parser's failure surface.
        function rlExtractMeta(text) {
            const src = text || '';
            const m = src.match(
                /\[\s*Bloom:?\s*L?(\d+)\s*[|·,]\s*PISA:?\s*[LP]?(\d+)\s*\]/i
            );
            if (!m) return { tags: '', stripped: src };
            const tags = 'Bloom L' + m[1] + ' · PISA L' + m[2];
            // Trim trailing whitespace/punctuation left over after stripping.
            const stripped = src.replace(m[0], '').replace(/[\s.;,]+$/, '').trim();
            return { tags: tags, stripped: stripped };
        }

        function rlRenderQuestion(idx) {
            const q = RL_SCENARIO.questions[idx];
            const total = (RL_SCENARIO.questions || []).length || 6;
            const badge = document.getElementById('rl-header-badge');
            if (badge) badge.textContent = RT('rl.question_of') + ' ' + (idx + 1) + ' / ' + total;

            // Pull Bloom/PISA tags out of the prompt and route to header meta.
            const meta = rlExtractMeta(q.prompt);
            const metaEl = document.getElementById('rl-q-header-meta');
            if (metaEl) metaEl.textContent = meta.tags;

            const promptEl = document.getElementById('rl-q' + (idx + 1) + '-prompt');
            // innerHTML — question prompt may contain inline images/SVGs/bold/italic.
            if (promptEl) promptEl.innerHTML = meta.stripped || '';

            // Per-question capture button. Any text-with-capture question
            // gets a dynamically-injected upload button right under the
            // input, with state tracked in stage6State.captureDone[idx].
            // Previously only Q3 had a hardcoded button, so other capture
            // questions could never satisfy the "upload your work" gate
            // and the submission was silently blocked → no AI call.
            const qBody = document.querySelector('#rl-q' + (idx + 1) + ' .rl-q-body');
            if (qBody) {
                const oldCap = qBody.querySelector('.rl-capture-area-dyn');
                if (oldCap) oldCap.remove();
                if (q.type === 'text-with-capture' && q.capture) {
                    const wrap = document.createElement('div');
                    wrap.className = 'rl-capture-area rl-capture-area-dyn';
                    wrap.innerHTML =
                        '<button type="button" class="rl-capture-btn" id="rl-q' + (idx + 1) + '-capture-btn">' +
                        RT('rl.upload_solution') + '</button>' +
                        '<div class="rl-capture-done" id="rl-q' + (idx + 1) + '-capture-done">' +
                        '<div class="rl-capture-confirm">' + RT('rl.solution_uploaded') + '</div>' +
                        '<div class="rl-capture-mock-img">📄</div>' +
                        '</div>';
                    // Insert before the feedback element so the capture row
                    // sits visually under the input.
                    const fb = qBody.querySelector('.rl-feedback');
                    if (fb) qBody.insertBefore(wrap, fb);
                    else qBody.appendChild(wrap);
                    const btnEl = wrap.querySelector('button');
                    if (btnEl) btnEl.addEventListener('click', () => rlCapture(idx));
                    // Restore the per-question done UI if the student already
                    // captured this Q earlier in the session.
                    if (stage6State.captureDone && stage6State.captureDone[idx]) {
                        if (btnEl) btnEl.classList.add('hidden');
                        const doneEl = wrap.querySelector('.rl-capture-done');
                        if (doneEl) doneEl.classList.add('show');
                    }
                }
            }

            // Per-question textarea injection. Q5 (and any other open-ended
            // RL question) authored with `open: true` lands as type=textarea
            // but the markup may only have a multi-input field group OR no
            // text input at all. Dynamically swap in a textarea so the
            // student has somewhere to type.
            if (q.type === 'textarea') {
                // Existing input in the markup (if any) — remove it.
                const existingInput = document.getElementById('rl-q' + (idx + 1) + '-input');
                if (existingInput && existingInput.tagName !== 'TEXTAREA') existingInput.remove();
                // Field-group container (used by multi-input markup) — clear.
                const fields = document.getElementById('rl-q' + (idx + 1) + '-fields');
                if (fields) fields.innerHTML = '';
                // Inject a textarea if not already there.
                let ta = document.getElementById('rl-q' + (idx + 1) + '-input');
                if (!ta || ta.tagName !== 'TEXTAREA') {
                    ta = document.createElement('textarea');
                    ta.id = 'rl-q' + (idx + 1) + '-input';
                    ta.className = 'rl-input rl-textarea';
                    ta.placeholder = RT('rl.textarea_placeholder');
                    ta.autocomplete = 'off';
                    ta.spellcheck = false;
                    const fb = qBody && qBody.querySelector('.rl-feedback');
                    if (qBody && fb) qBody.insertBefore(ta, fb);
                    else if (qBody) qBody.appendChild(ta);
                }
                ta.value = '';
            }

            if (q.type === 'multi-input') {
                const container = document.getElementById('rl-q' + (idx + 1) + '-fields');
                if (container) {
                    container.innerHTML = '';
                    q.fields.forEach((f, i) => {
                        const row = document.createElement('div');
                        row.className = 'rl-field-row';
                        const lbl = document.createElement('div');
                        lbl.className = 'rl-field-label';
                        lbl.textContent = f.label;
                        const inp = document.createElement('input');
                        inp.className = 'rl-input rl-field-input';
                        inp.type = 'text';
                        inp.inputMode = 'text';
                        inp.autocomplete = 'off';
                        inp.dataset.fieldIndex = i;
                        row.appendChild(lbl);
                        row.appendChild(inp);
                        container.appendChild(row);
                    });
                }
            }

            // Slots q2 and q5 ship with only a <div class="rl-field-group"> placeholder,
            // not a static <input>. When their question lands as 'text' or
            // 'text-with-capture' (single-answer authored without fields[]),
            // the student would see no input box. Inject one on demand.
            if (q.type === 'text' || q.type === 'text-with-capture') {
                const fieldsDiv = document.getElementById('rl-q' + (idx + 1) + '-fields');
                if (fieldsDiv) fieldsDiv.innerHTML = '';
                let inp = document.getElementById('rl-q' + (idx + 1) + '-input');
                if (!inp || inp.tagName !== 'INPUT') {
                    if (inp) inp.remove();
                    inp = document.createElement('input');
                    inp.id = 'rl-q' + (idx + 1) + '-input';
                    inp.className = 'rl-input';
                    inp.type = 'text';
                    inp.inputMode = 'text';
                    inp.placeholder = 'Javobingiz...';
                    inp.autocomplete = 'off';
                    inp.autocorrect = 'off';
                    inp.spellcheck = false;
                    const promptEl = document.getElementById('rl-q' + (idx + 1) + '-prompt');
                    const anchor = (fieldsDiv && fieldsDiv.parentNode) ? fieldsDiv : promptEl;
                    if (anchor && anchor.parentNode) {
                        anchor.parentNode.insertBefore(inp, anchor.nextSibling);
                    } else if (qBody) {
                        const fb = qBody.querySelector('.rl-feedback');
                        if (fb) qBody.insertBefore(inp, fb); else qBody.appendChild(inp);
                    }
                } else {
                    inp.value = '';
                }
            }

            rlHideFeedback('rl-q' + (idx + 1) + '-fb');

            // Per-question buttons. Replaces the legacy "submit via the bottom
            // action button" pattern: each question now owns its own submit,
            // optional hint toggle, optional tutor pre-submit, and a post-
            // grading Keyingi. Re-render safe — the entire row group is rebuilt
            // every time rlRenderQuestion fires.
            if (qBody) {
                // Tear down anything from a prior render of this slot.
                qBody.querySelectorAll('.rl-q-actions, .rl-hint-panel, .rl-q-after').forEach(el => el.remove());

                const fb = qBody.querySelector('.rl-feedback');

                // Pre-submit action row.
                const actions = document.createElement('div');
                actions.className = 'rl-q-actions';
                const submitBtn = document.createElement('button');
                submitBtn.type = 'button';
                submitBtn.className = 'rl-submit-local';
                submitBtn.id = 'rl-q' + (idx + 1) + '-submit';
                submitBtn.textContent = RT('btn.send');
                submitBtn.addEventListener('click', () => rlSubmitQuestion());
                actions.appendChild(submitBtn);

                if (q.hint) {
                    const hintBtn = document.createElement('button');
                    hintBtn.type = 'button';
                    hintBtn.className = 'rl-hint-toggle';
                    hintBtn.id = 'rl-q' + (idx + 1) + '-hint-toggle';
                    hintBtn.setAttribute('aria-expanded', 'false');
                    hintBtn.textContent = RT('btn.show_hint');
                    hintBtn.addEventListener('click', () => rlToggleHint(idx));
                    actions.appendChild(hintBtn);
                }

                const tutorBtn = document.createElement('button');
                tutorBtn.type = 'button';
                tutorBtn.className = 'rl-tutor-pre-submit';
                tutorBtn.id = 'rl-q' + (idx + 1) + '-tutor';
                tutorBtn.textContent = RT('btn.ask_tutor');
                tutorBtn.addEventListener('click', () => rlAskTutor(idx));
                actions.appendChild(tutorBtn);

                // Hint panel — collapsed by default.
                const hintPanel = document.createElement('div');
                hintPanel.className = 'rl-hint-panel';
                hintPanel.id = 'rl-q' + (idx + 1) + '-hint-panel';
                hintPanel.hidden = true;
                if (q.hint) hintPanel.textContent = q.hint;

                // Post-grading row — hidden until verdict is set.
                const after = document.createElement('div');
                after.className = 'rl-q-after';
                after.id = 'rl-q' + (idx + 1) + '-after';
                after.hidden = true;
                const nextBtn = document.createElement('button');
                nextBtn.type = 'button';
                nextBtn.className = 'rl-next-local';
                nextBtn.id = 'rl-q' + (idx + 1) + '-next';
                nextBtn.textContent = RT('btn.next_question');
                nextBtn.addEventListener('click', () => rlAdvanceFromQuestion());
                after.appendChild(nextBtn);

                // Insertion order: actions row → hint panel → existing feedback → after row.
                if (fb) {
                    qBody.insertBefore(actions, fb);
                    qBody.insertBefore(hintPanel, fb);
                    fb.insertAdjacentElement('afterend', after);
                } else {
                    qBody.appendChild(actions);
                    qBody.appendChild(hintPanel);
                    qBody.appendChild(after);
                }
            }

            // Reset per-question runtime flags so a re-render gives a clean slot.
            if (stage6State.checking) stage6State.checking[idx] = false;
            if (stage6State.hintOpen) stage6State.hintOpen[idx] = false;
        }

        function rlShowQuestion(idx) {
            for (let i = 1; i <= 6; i++) {
                const el = document.getElementById('rl-q' + i);
                if (el) el.classList.remove('rl-active');
            }
            // Story panel stays visible alongside the question — it's the
            // student's reference passage, not a separate "screen". Only
            // the closure card is mutually exclusive with the question.
            const closure = document.getElementById('rl-closure');
            if (closure) closure.classList.remove('rl-active');

            const target = document.getElementById('rl-q' + (idx + 1));
            if (!target) return;

            rlRenderQuestion(idx);
            target.classList.add('rl-active');
            stage6State.qIndex = idx;
            stage6State.screen = 'q' + (idx + 1);

            // The fixed bottom button is now phase-level only — submit and
            // next happen via per-question local buttons (.rl-submit-local /
            // .rl-next-local). Hide the bottom button while we're in the
            // question loop; rlShowClosure() re-shows it for the phase-end
            // advance.
            const ab = document.getElementById('action-button');
            if (ab) ab.style.display = 'none';
        }

        function rlAnimateTransition(fromEl, toEl, onDone) {
            if (!fromEl || !toEl) { if (onDone) onDone(); return; }
            fromEl.classList.add('rl-anim-out');
            setTimeout(() => {
                fromEl.classList.remove('rl-anim-out');
                fromEl.classList.remove('rl-active');
                fromEl.style.display = '';
                toEl.classList.add('rl-active');
                toEl.classList.add('rl-anim-in');
                setTimeout(() => {
                    toEl.classList.remove('rl-anim-in');
                    if (onDone) onDone();
                }, 360);
            }, 330);
        }

        function rlMorphButton(label) {
            btn.classList.remove('pulse', 'state-line', 'state-start');
            btn.classList.add('state-pill');
            setBtnText(label);
        }

        // Tracks pending AI tutor lookups for real-life questions, keyed by
        // question index — guards against stale responses overwriting the
        // current view.
        let rlPendingAi = null;
        let rlPendingAiTimer = null;

        // While AI is grading we lock the active question's local submit
        // button (was: the global #action-button). The lock is paired with
        // stage6State.checking[idx] for the data-side guard; this CSS lock
        // is the visible/UI affordance. The 12s safety timeout still fires
        // so a dropped nets:result event can't permanently freeze the
        // button.
        const RL_AI_LOCK_TIMEOUT_MS = 12000;
        function setRlAiLock(locked, idx) {
            // idx is optional — when omitted we look up the active question.
            const i = (typeof idx === 'number') ? idx : (stage6State && stage6State.qIndex);
            const btn = document.getElementById('rl-q' + ((i || 0) + 1) + '-submit');
            if (!btn) return;
            if (locked) {
                btn.disabled = true;
                btn.setAttribute('aria-busy', 'true');
            } else {
                btn.disabled = false;
                btn.removeAttribute('aria-busy');
            }
        }

        function rlClearAiPending() {
            if (rlPendingAiTimer) {
                clearTimeout(rlPendingAiTimer);
                rlPendingAiTimer = null;
            }
            // If the lock fired but no result came back (safety timeout),
            // also clear the per-question busy flag so the student isn't
            // stuck. submitted[idx] stays false so they get redirected to
            // a verdict on next submit attempt.
            if (rlPendingAi && stage6State.checking) {
                stage6State.checking[rlPendingAi.qIndex] = false;
            }
            const lockIdx = rlPendingAi ? rlPendingAi.qIndex : undefined;
            rlPendingAi = null;
            setRlAiLock(false, lockIdx);
        }

        function rlDispatchTutorAi(idx, q, val) {
            const ticket = { qIndex: idx };
            rlPendingAi = ticket;
            setRlAiLock(true);
            // Safety net: if the tutor pipeline never fires `nets:result`
            // (transport drop, widget crash, etc.) the button must still
            // recover so the student isn't stuck on this question.
            if (rlPendingAiTimer) clearTimeout(rlPendingAiTimer);
            rlPendingAiTimer = setTimeout(() => {
                if (rlPendingAi === ticket) rlClearAiPending();
            }, RL_AI_LOCK_TIMEOUT_MS);
            try {
                // FE-7: this dispatcher uses guidance_type for verdict
                // detection (real-life challenge answer-equivalence check).
                // The new tutorChat endpoint does not surface guidance_type,
                // so this caller stays on the legacy tutor() path explicitly
                // via kind: 'legacy-tutor' (no more bare 'tutor'). Free-form
                // tutor chat in the widget calls window.NETS_AI.tutorChat()
                // directly, not via this event bridge.
                document.dispatchEvent(new CustomEvent('nets:submit', { detail: {
                    kind: 'legacy-tutor',
                    payload: {
                        phase: 'real-life',
                        question: q.prompt || q.label || ('Savol ' + (idx + 1)),
                        studentInput: val,
                        context: (q.acceptableAnswers || []).join(' | '),
                    },
                }}));
            } catch (e) {
                rlClearAiPending();
            }
            return ticket;
        }

        // Mark the question committed (verdict shown, no retry). Hides the
        // pre-submit row and reveals the local Keyingi button. Used by the
        // local-correct path AND by the AI-result handler when the verdict
        // arrives. Idempotent.
        function rlCommitQuestion(idx) {
            const actions = document.querySelector('#rl-q' + (idx + 1) + ' .rl-q-actions');
            const after = document.getElementById('rl-q' + (idx + 1) + '-after');
            if (actions) actions.style.display = 'none';
            if (after) after.hidden = false;
        }

        // Single-check submit handler. Per design rule: local exact-match
        // first; if the answer matches a canonical form, ✓ immediately and
        // we don't bill an AI call. Only when the local check rejects do we
        // dispatch the AI to evaluate equivalent forms (e.g. (7a-4b)(7a+4b)
        // vs (7a+4b)(7a-4b) — algebraically same but textually different).
        // The verdict is final; no retry. Pre-fix code dual-fired (local
        // hint AND AI dispatch) on first wrong attempt, which produced
        // overlapping feedback and confused students.
        function rlSubmitQuestion() {
            if (state.isAnimating) return;
            const idx = stage6State.qIndex;
            const q = RL_SCENARIO.questions[idx];
            const fbId = 'rl-q' + (idx + 1) + '-fb';

            // Guard against double-submit during in-flight AI checks.
            if (stage6State.checking && stage6State.checking[idx]) return;
            // Guard against re-firing after the verdict is already in.
            if (stage6State.submitted[idx]) return;

            // Branch by question type for input validation + local checker.
            // After validation, every path converges on rlCommitOrAi() below.
            let val = '';
            let studentSubmissionPayload = '';
            let canLocalCheck = false;
            let localCorrect = false;

            if (q.type === 'text' || q.type === 'text-with-capture') {
                const inp = document.getElementById('rl-q' + (idx + 1) + '-input');
                val = inp ? inp.value.trim() : '';

                if (q.type === 'text-with-capture' && !(stage6State.captureDone && stage6State.captureDone[idx])) {
                    rlSetFeedback(fbId, 'rl-hint', RT('rl.upload_required'));
                    return;
                }
                if (!val) {
                    rlSetFeedback(fbId, 'rl-hint', RT('rl.enter_answer'));
                    return;
                }

                canLocalCheck = Array.isArray(q.acceptableAnswers) && q.acceptableAnswers.length > 0;
                localCorrect = canLocalCheck && rlMatchText(val, q.acceptableAnswers);
                studentSubmissionPayload = val;

            } else if (q.type === 'multi-input') {
                const container = document.getElementById('rl-q' + (idx + 1) + '-fields');
                const inputs = container ? container.querySelectorAll('input') : [];
                const anyEmpty = Array.from(inputs).some(i => !i.value.trim());
                if (anyEmpty) {
                    rlSetFeedback(fbId, 'rl-hint', RT('rl.fill_all_fields'));
                    return;
                }

                canLocalCheck = Array.isArray(q.fields) && q.fields.length > 0;
                localCorrect = canLocalCheck && rlMatchMulti(q.fields, Array.from(inputs));
                studentSubmissionPayload = Array.from(inputs).map((inp, ii) => {
                    const lbl = (q.fields[ii] && q.fields[ii].label) || ('field' + ii);
                    return lbl + '=' + (inp.value || '').trim();
                }).join(' · ');

            } else if (q.type === 'textarea') {
                const inp = document.getElementById('rl-q' + (idx + 1) + '-input');
                val = inp ? inp.value.trim() : '';
                if (val.length < 20) {
                    rlSetFeedback(fbId, 'rl-hint', RT('rl.min_chars'));
                    return;
                }
                // Open-ended: no local checker — straight to AI.
                canLocalCheck = false;
                studentSubmissionPayload = val;
            } else {
                // Unknown type — bail without state mutation.
                return;
            }

            // From here we commit to one check path. Engage the busy lock
            // and disable the local submit button so a second click can't
            // re-enter this function. Hide the tutor pre-submit since the
            // student has now committed (no more help available — verdict
            // is final).
            stage6State.checking[idx] = true;
            const submitBtn = document.getElementById('rl-q' + (idx + 1) + '-submit');
            if (submitBtn) submitBtn.disabled = true;
            const tutorBtn = document.getElementById('rl-q' + (idx + 1) + '-tutor');
            if (tutorBtn) tutorBtn.style.display = 'none';

            // Path 1 — local check passed: instant ✓, no AI call.
            if (canLocalCheck && localCorrect) {
                stage6State.correct[idx] = true;
                stage6State.submitted[idx] = true;
                stage6State.checking[idx] = false;
                rlSetFeedback(fbId, 'rl-correct', RT('rl.correct_prefix') +
                    (q.type === 'text-with-capture' ? (q.expectedWork || '') : ''));
                if (window.__sessionLog) {
                    window.__sessionLog.push({
                        phase: 'real-life', id: q.id || ('rl-' + (idx + 1)),
                        correct: true, score: 1, first_try: true, closed: true,
                    });
                }
                rlCommitQuestion(idx);
                return;
            }

            // Path 2 — local rejected (or no local possible for textarea):
            // dispatch AI ONCE. The result handler at nets:result will:
            //   • update the band to rl-correct (✓) or rl-wrong (✗)
            //   • set submitted[idx] = true and clear checking[idx]
            //   • call rlCommitQuestion to reveal Keyingi
            stage6State.attempts[idx]++;
            rlSetFeedback(fbId, 'rl-loading', '');
            rlDispatchTutorAi(idx, q, studentSubmissionPayload);
        }

        // AI tutor result listener for real-life questions. Updates the
        // currently-displayed feedback bubble with AI-generated text. If the
        // AI errors / falls back, the local "incorrect" state is kept verbatim.
        document.addEventListener('nets:result', (ev) => {
            const detail = ev.detail || {};
            // FE-7: dispatcher above migrated from bare 'tutor' to 'legacy-tutor'.
            if (detail.kind !== 'legacy-tutor') return;
            const ticket = rlPendingAi;
            if (!ticket) return;
            // User moved on to the next question already — drop stale response.
            if (ticket.qIndex !== stage6State.qIndex) { rlClearAiPending(); return; }
            const result = detail.result || {};
            const fbId = 'rl-q' + (ticket.qIndex + 1) + '-fb';
            const fbEl = document.getElementById(fbId);
            // Graceful degrade — keep whatever local feedback is already shown.
            if (result._fallback || result._error || result._offline) { rlClearAiPending(); return; }
            // Tutor endpoint returns {response, guidance_type}. There's no canonical
            // "correct" boolean — we infer correctness from guidance_type if it's
            // explicitly "validation" with a positive response, otherwise treat
            // as nuanced wrong-feedback to display.
            const response = result.response || '';
            const guidance = (result.guidance_type || '').toLowerCase();
            const aiCorrect = guidance === 'validation' || guidance === 'correct';
            if (!fbEl) { rlClearAiPending(); return; }
            if (aiCorrect) {
                stage6State.correct[ticket.qIndex] = true;
                stage6State.submitted[ticket.qIndex] = true;
                rlSetFeedback(
                    fbId,
                    'rl-correct',
                    response || RT('reading.ai_correct_default'),
                    { aiBadge: true, showTutor: false }
                );
                if (window.__sessionLog) {
                    const q = RL_SCENARIO.questions[ticket.qIndex];
                    const ax1 = (detail && detail.axis_1) || 3;
                    const ax2 = (detail && detail.axis_2) || 3;
                    window.__sessionLog.push({
                        phase: 'real-life', id: (q && q.id) || ('rl-' + (ticket.qIndex + 1)),
                        correct: true, score: typeof (detail && detail.score) === 'number' ? detail.score : 1,
                        axis_1: ax1, axis_2: ax2, first_try: false,
                    });
                }
            } else if (response) {
                // AI returned a wrong/uncertain verdict. Always switch to
                // rl-wrong (with the ✗ pill); pre-fix code preserved the
                // hint color and the wrong band looked like a hint. No
                // tutor fallback in the band — the student already had
                // the chance to ask the tutor BEFORE submitting.
                stage6State.submitted[ticket.qIndex] = true;
                rlSetFeedback(
                    fbId,
                    'rl-wrong',
                    response,
                    { aiBadge: true, showTutor: false }
                );
            } else {
                // No response and no aiCorrect — treat as wrong with a
                // generic message so the student isn't left in limbo.
                stage6State.submitted[ticket.qIndex] = true;
                rlSetFeedback(
                    fbId,
                    'rl-wrong',
                    RT('rl.ai_unavailable_wrong'),
                    { aiBadge: false, showTutor: false }
                );
            }
            // Clear the busy lock and reveal the local Keyingi button so
            // the student can move on. submitted[idx] is set in every
            // branch above — rlCommitQuestion is idempotent so no harm
            // double-calling.
            stage6State.checking[ticket.qIndex] = false;
            rlCommitQuestion(ticket.qIndex);
            rlClearAiPending();
        });

        function rlAdvanceFromQuestion() {
            if (state.isAnimating) return;
            state.isAnimating = true;
            const idx = stage6State.qIndex;
            const total = (RL_SCENARIO.questions || []).length || 6;
            // Real student action: just submitted answer for question `idx`
            // (the only path into rlAdvanceFromQuestion is after submitted[idx]
            // is set true). Mirror submitted-count into completion progress so
            // the dot 5 segment partial-fills with each answer.
            const answeredCount = stage6State.submitted.filter(Boolean).length;
            setPhaseProgress('realLife', answeredCount, total);

            if (idx < total - 1) {
                const curEl = document.getElementById('rl-q' + (idx + 1));
                const nextIdx = idx + 1;
                rlRenderQuestion(nextIdx);
                const nextEl = document.getElementById('rl-q' + (nextIdx + 1));

                stage6State.qIndex = nextIdx;
                stage6State.screen = 'q' + (nextIdx + 1);

                const badge = document.getElementById('rl-header-badge');
                if (badge) badge.textContent = RT('rl.question_of') + ' ' + (nextIdx + 1) + ' / ' + total;

                rlAnimateTransition(curEl, nextEl, () => {
                    rlMorphButton(RT('btn.submit_response'));
                    state.isAnimating = false;
                });
            } else {
                rlShowClosure();
            }
        }

        function rlShowClosure() {
            const lastQ = document.getElementById('rl-q6');
            const closure = document.getElementById('rl-closure');
            if (!closure) { state.isAnimating = false; return; }

            const correctCount = stage6State.correct.filter(Boolean).length;
            const captureCount = stage6State.captureCount;

            const banner = document.getElementById('rl-closure-banner');
            const msg = document.getElementById('rl-closure-msg');
            const stats = document.getElementById('rl-closure-stats');

            if (banner) { banner.style.animation = 'none'; banner.textContent = RL_SCENARIO.closure.title; void banner.offsetHeight; banner.style.animation = ''; }
            if (msg) { msg.style.animation = 'none'; msg.textContent = RL_SCENARIO.closure.message; void msg.offsetHeight; msg.style.animation = ''; }
            if (stats) { stats.style.animation = 'none'; stats.textContent = RT('rl.correct_count') + ' ' + correctCount + ' / 6' + (captureCount > 0 ? ' · ' + RT('rl.uploaded_count') + ' ' + captureCount : ''); void stats.offsetHeight; stats.style.animation = ''; }

            if (lastQ) lastQ.classList.remove('rl-active');
            const badge = document.getElementById('rl-header-badge');
            if (badge) badge.textContent = RL_SCENARIO.title;
            // Closure isn't a question — clear meta so it hides.
            const closureMetaEl = document.getElementById('rl-q-header-meta');
            if (closureMetaEl) closureMetaEl.textContent = '';

            closure.classList.add('rl-active');
            stage6State.screen = 'closure';

            // Re-show the fixed bottom button for the phase-end advance —
            // it was hidden during the question loop because each question
            // had its own local submit/next buttons.
            const ab = document.getElementById('action-button');
            if (ab) ab.style.display = '';

            btn.classList.remove('pulse');
            rlMorphButton(RT('btn.next_stage'));
            btn.classList.add('pulse');
            state.isAnimating = false;
        }

        function rlShowEndPlaceholder() {
            state.isAnimating = true;
            // Real Life phase done — student finished the scenario or skipped.
            completePhase('realLife');
            const screen6 = document.getElementById('screen-6');
            if (screen6) { screen6.style.transition = 'opacity 400ms ease'; screen6.style.opacity = '0'; }
            btn.classList.remove('pulse', 'state-pill');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            setTimeout(() => {
                if (screen6) { screen6.classList.remove('active'); screen6.style.opacity = ''; screen6.style.transition = ''; }
                state.isAnimating = false;
                // Wave 2: Consolidation sits between Real-Life and Boss (auto-skip if empty).
                if (typeof showConsolidationScreen === 'function' && consolidationHasContent()) {
                    showConsolidationScreen(startFinalBoss);
                } else {
                    startFinalBoss();
                }
            }, 450);
        }

        function startStage6() {
            setStage(6);
            // Real Life is a fixed 6-question scenario in this template; the
            // submitted[] array is what the runtime fills as the student
            // answers each one. Mirror that into completionState.
            setPhaseRequired('realLife', 6);
            const allScreens = document.querySelectorAll('.screen');
            allScreens.forEach(s => s.classList.remove('active'));

            const s6 = document.getElementById('screen-6');
            if (s6) s6.classList.add('active');

            stage6State.screen = 'story';
            stage6State.qIndex = 0;
            stage6State.attempts = [0, 0, 0, 0, 0, 0];
            stage6State.correct = [false, false, false, false, false, false];
            stage6State.captureDone = [false, false, false, false, false, false];
            stage6State.captureQ3Done = false;
            stage6State.submitted = [false, false, false, false, false, false];
            stage6State.checking = [false, false, false, false, false, false];
            stage6State.hintOpen = [false, false, false, false, false, false];
            stage6State.captureCount = 0;

            for (let i = 1; i <= 6; i++) {
                const el = document.getElementById('rl-q' + i);
                if (el) el.classList.remove('rl-active');
            }
            const closure = document.getElementById('rl-closure');
            if (closure) closure.classList.remove('rl-active');

            const story = document.getElementById('rl-story-section');
            // Reset to CSS defaults — pre-pagination code force-set flex:1
            // here so the story would fill the card; new design relies on
            // .rl-story-wrap's clamp() bound the panel height.
            if (story) { story.style.display = ''; story.style.flex = ''; }

            const scroll = document.getElementById('rl-story-scroll');
            if (scroll && !scroll.hasChildNodes()) {
                // Defer pagination two animation frames so the card has
                // had a chance to lay out (it starts at opacity:0 here and
                // may not yet have a real clientHeight on the panel —
                // measuring too early gives 0 → fallback height → wrong
                // page count).
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        rlRenderStory();
                    });
                });
            }

            const badge = document.getElementById('rl-header-badge');
            if (badge) badge.textContent = RT('rl.task_badge') + ' · ' + (RL_SCENARIO.title || RL_SCENARIO.badge || '');

            // Bug #6: hide the WHOLE rl-card during the announcement, not
            // just rl-story-section. The card chrome (badge, story, buttons)
            // would otherwise show up behind the announcement card so the
            // student sees them simultaneously. Fade in after the card lands.
            const rlCard = document.getElementById('rl-card');
            if (rlCard) { rlCard.style.transition = 'none'; rlCard.style.opacity = '0'; }
            // Defensive: drop `tm-dock-hidden` here too. Primary cleanup
            // lives in gbExitToStage6; this is the safety net for any other
            // entry paths into RL (session restore, skip shortcuts) that
            // might land here with the class still applied from a prior
            // Tile Match dock state — CSS would otherwise force opacity:0
            // and the "Boshlash" pill stays invisible.
            btn.classList.remove('pulse', 'state-line', 'state-start', 'state-pill', 'tm-dock-hidden');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            playPhaseAnnouncement('phase.real_life', () => {
                if (rlCard) { rlCard.style.transition = 'opacity 300ms ease'; rlCard.style.opacity = '1'; }
                btn.classList.remove('state-line');
                btn.classList.add('state-pill', 'pulse');
                setBtnText(RT('btn.start'));
                if (btnText) btnText.style.opacity = '';
            });
        }

        function rlHandleAction() {
            if (stage6State.screen === 'story') {
                // Story panel stays visible permanently as a reference; only
                // the question slot reveals on Start. Pre-pagination code
                // faded out and display:none'd the story here, which broke
                // the "passage stays alongside the question" contract.
                btn.classList.remove('pulse');
                rlShowQuestion(0);
                return;
            }
            if (stage6State.screen === 'closure') {
                rlShowEndPlaceholder();
                return;
            }
            const submitted = stage6State.submitted[stage6State.qIndex];
            if (submitted) {
                rlAdvanceFromQuestion();
            } else {
                rlSubmitQuestion();
            }
        }

        /* ── STAGE 7 · FINAL BOSS ───────────────────────────── */

        const BOSS_QUESTIONS = [
            { id:'E1', tier:'easy',   damage:10, bloom:'L3', pisa:'L3',
              prompt:'Yeching: x² = 64',
              acceptable:['±8','x=±8','x=8,x=-8','8va-8','8,-8','+8,-8'],
              hints:['x² = 64 → ikkala tomondan kvadrat ildiz oling','√64 nechaga teng?','x = ±√64 = ±8']
            },
            { id:'E2', tier:'easy',   damage:10, bloom:'L3', pisa:'L3',
              prompt:'Yeching: x² = 0',
              acceptable:['0','x=0'],
              hints:['Qaysi son 0 ga kvadrat bo\'ladi?','Bitta ildiz bor','x = 0']
            },
            { id:'E3', tier:'easy',   damage:10, bloom:'L3', pisa:'L3',
              prompt:'Yeching: x² + 16 = 0',
              acceptable:["haqiqiyildizyoq","ildizyoq","yechimyoq","yo'q","yoq"],
              hints:['x² = −16 ko\'rinishiga keltiring','Haqiqiy son kvadrati manfiy bo\'la oladimi?','Haqiqiy ildiz yo\'q — x² < 0 mumkin emas']
            },
            { id:'E4', tier:'easy',   damage:10, bloom:'L3', pisa:'L3',
              prompt:'Yeching: x² – 36 = 0',
              acceptable:['±6','x=±6','x=6,x=-6','6va-6','6,-6','+6,-6'],
              hints:['x² = 36 ko\'rinishiga keltiring','√36 = ?','x = ±6']
            },
            { id:'M1', tier:'medium', damage:20, bloom:'L4', pisa:'L4',
              prompt:'Yeching: x² + 7x + 12 = 0',
              acceptable:['-3va-4','-4va-3','x=-3,x=-4','x=-4,x=-3','-3,-4','-4,-3'],
              hints:['p + q = 7 va p · q = 12 bo\'lgan juft toping','3 + 4 = 7 va 3 × 4 = 12 ✓','(x+3)(x+4) = 0 → x = −3 yoki x = −4']
            },
            { id:'M2', tier:'medium', damage:20, bloom:'L4', pisa:'L4',
              prompt:'Yeching: x² – 5x + 6 = 0',
              acceptable:['2va3','3va2','x=2,x=3','x=3,x=2','2,3','3,2'],
              hints:['p + q = −5 va p · q = 6 bo\'lgan juft toping','−2 + (−3) = −5 va (−2)×(−3) = 6 ✓','(x−2)(x−3) = 0 → x = 2 yoki x = 3']
            },
            { id:'M3', tier:'medium', damage:20, bloom:'L4', pisa:'L4',
              prompt:'Yeching: x² + 3x – 10 = 0',
              acceptable:['2va-5','-5va2','x=2,x=-5','x=-5,x=2','2,-5','-5,2'],
              hints:['p + q = 3 va p · q = −10 bo\'lgan juft toping','5 + (−2) = 3 va 5×(−2) = −10 ✓','(x−2)(x+5) = 0 → x = 2 yoki x = −5']
            },
            { id:'M4', tier:'medium', damage:20, bloom:'L4', pisa:'L4',
              prompt:'Yeching: x² – x – 20 = 0',
              acceptable:['5va-4','-4va5','x=5,x=-4','x=-4,x=5','5,-4','-4,5'],
              hints:['p + q = −1 va p · q = −20 bo\'lgan juft toping','4 + (−5) = −1 va 4×(−5) = −20 ✓','(x−5)(x+4) = 0 → x = 5 yoki x = −4']
            },
            { id:'H1', tier:'hard',   damage:30, bloom:'L5', pisa:'L5',
              prompt:'x² + bx – 12 = 0 tenglamasining ildizlari 3 va −4. b ni toping.',
              acceptable:['1','b=1'],
              hints:['(x−3)(x+4) = 0 ko\'rinishiga keltiring','Ochganda: x² + (4−3)x − 12 = x² + x − 12','b = 4 − 3 = 1']
            },
            { id:'H2', tier:'hard',   damage:30, bloom:'L5', pisa:'L5',
              prompt:'Yig\'indisi 13, ko\'paytmasi 42 bo\'lgan ikkita sonni toping.',
              acceptable:['6va7','7va6','6,7','7,6','6 va 7','7 va 6'],
              hints:['Sonlarni x va 13−x deb belgilang','x(13−x) = 42 → x²−13x+42 = 0','p+q=13 va p·q=42 → (6, 7)']
            }
        ];

        const BOSS_META = __BOSS_META__;

        function bossDynamicEnabledFromMeta() {
            return Boolean(
                typeof BOSS_META !== 'undefined' &&
                BOSS_META &&
                BOSS_META.use_dynamic_boss === true
            );
        }

        const bossState = {
            hp:100, maxHp:100, qIndex:0, combo:0,
            hintsUsed:0, hintStep:0, correct:0, answered:false, done:false,
            persona_traits: ['mentor'], // Wave F3: set by initBossPlan()
            // FB redesign — additive runtime fields (Chunk B contract).
            sessionId: null,        // minted by bossInit()
            attemptsUsed: 0,        // increments per wrong submit (server-mirrored)
            outcome: null,          // 'expert' | 'strong' | 'passing' | 'hali_emas'
            stars: 0,               // 0–3 (server returns on done)
            outcomeXp: 0,           // total XP awarded on done
            busy: false,            // gates concurrent submits (TM/RLC pattern)
            lastDamage: 0,          // damage dealt last turn (for visual flash)
            damageDealt: 0,         // running total — for result summary
            // FE-5 — Plan 5 dynamic boss loop fields.
            bossSessionId: null,        // returned by bossStart (server-side arc id)
            trialsLeft: null,           // mirrored from server submit-answer
            currentQuestion: null,      // last bossGenerateQuestion response (whitelisted)
            currentDifficulty: null,    // server-side difficulty signal
            recentBossPhrases: [],      // last ≤5 question_text snippets — anti-repetition
            useDynamicBoss: bossDynamicEnabledFromMeta(), // author opt-in — falls back to BOSS_QUESTIONS path on failure
            kickoffExpired: false,      // FE-5 race guard — set true when 3s startFinalBoss timeout wins; late LLM responses must NOT clobber legacy-mode state
        };

        // Wave F3 — load personalised boss plan (ordering + framing + persona).
        // Runs once at boss-start, before the first question renders.
        // Uses localStorage as a refresh-recovery cache so a mid-boss reload keeps
        // the same ordering.  Falls back to default order + 'mentor' on any error.
        async function initBossPlan() {
            const hwId = (typeof state !== 'undefined' && state.hwId)
                ? state.hwId
                : (window.NETS_CTX && window.NETS_CTX.hwId) || '';
            const cacheKey = 'nets_boss_plan_' + hwId;
            let plan = null;

            // 1. Try localStorage (refresh-recovery).
            try {
                const raw = localStorage.getItem(cacheKey);
                if (raw) plan = JSON.parse(raw);
            } catch (e) { plan = null; }

            // 2. If no cache, fetch from backend.
            if (!plan) {
                try {
                    plan = await window.NETS_AI.bossPlan({
                        session_id: localStorage.getItem('nets_tutor_session'),
                        hw_id: hwId,
                    });
                    localStorage.setItem(cacheKey, JSON.stringify(plan));
                } catch (err) {
                    console.warn('[F3] boss-plan fetch failed, using default order:', err);
                    plan = {
                        ordered: BOSS_QUESTIONS.map(q => ({
                            question_id: q.id || q.question_id,
                            framing_text: '',
                        })),
                        persona_traits: ['mentor'],
                    };
                }
            }

            // 3. Validate and apply ordering.
            if (plan && Array.isArray(plan.ordered) && plan.ordered.length) {
                const byId = new Map(BOSS_QUESTIONS.map(q => [q.id || q.question_id, q]));
                const reordered = plan.ordered
                    .map(o => {
                        const q = byId.get(o.question_id);
                        return q ? Object.assign({}, q, { _framing: o.framing_text || '' }) : null;
                    })
                    .filter(Boolean);

                if (reordered.length === BOSS_QUESTIONS.length) {
                    // Replace in-place so existing references stay valid.
                    BOSS_QUESTIONS.length = 0;
                    reordered.forEach(q => BOSS_QUESTIONS.push(q));
                } else {
                    console.warn('[F3] boss-plan ordering incomplete; falling back to default');
                    // Keep existing order, just add empty _framing.
                    BOSS_QUESTIONS.forEach(q => { if (!('_framing' in q)) q._framing = ''; });
                }
            } else {
                BOSS_QUESTIONS.forEach(q => { if (!('_framing' in q)) q._framing = ''; });
            }

            // 4. Store persona_traits on bossState.
            bossState.persona_traits = (
                Array.isArray(plan && plan.persona_traits) && plan.persona_traits.length
            ) ? plan.persona_traits : ['mentor'];
        }

        function startFinalBoss() {
            setStage(7);
            // Boss phase: 1 unit per boss question. Required is set from the
            // (possibly reordered) BOSS_QUESTIONS array, which initBossPlan
            // has already finalised by this point.
            const bossTotal = (typeof BOSS_QUESTIONS !== 'undefined' && Array.isArray(BOSS_QUESTIONS))
                ? BOSS_QUESTIONS.length : 1;
            setPhaseRequired('boss', bossTotal);
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            const sb = document.getElementById('screen-boss');
            if (sb) sb.classList.add('active');

            // Defensive: the RL phase hides #action-button via inline
            // display:none during its question loop and rlShowClosure()
            // re-shows it on the closure card. Normal flow goes
            // RL-Q6 → rlShowClosure (un-hides) → rlShowEndPlaceholder → here.
            // But edge paths (skip-to-end shortcuts, mid-RL exits, session
            // restore landing on Boss) can reach this entry with the
            // button still hidden, leaving the student stuck. Re-show
            // unconditionally so Boss is self-contained. Also strip
            // `tm-dock-hidden` (Tile Match dock-hide class — CSS rule
            // `opacity: 0 !important`) which can leak across phases when
            // the GB→RL→Boss path doesn't route through gbSetButtonNext.
            const ab = document.getElementById('action-button');
            if (ab) ab.style.display = '';
            if (ab) ab.classList.remove('tm-dock-hidden');

            Object.assign(bossState, {
                hp:100,maxHp:100,qIndex:0,combo:0,hintsUsed:0,hintStep:0,correct:0,answered:false,done:false,
                bossSessionId:null,trialsLeft:null,currentQuestion:null,currentDifficulty:null,recentBossPhrases:[],
                useDynamicBoss: bossDynamicEnabledFromMeta(),
            });
            // persona_traits intentionally NOT reset here — initBossPlan sets it once.
            // FB redesign — mint sessionId, reset attempts/outcome/stars/etc, apply
            // BOSS_META overrides (starting_hp_override, boss_type → data attribute).
            try { bossInit(); } catch (e) { console.warn('[FB] bossInit failed:', e); }

            btn.classList.remove('pulse','state-pill','tm-dock-hidden');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';

            const intro   = document.getElementById('boss-intro-card');
            const battle  = document.getElementById('boss-battle');
            const victory = document.getElementById('boss-victory');
            const defeat  = document.getElementById('boss-defeat');
            if (intro)   { intro.style.cssText   = ''; }
            if (battle)  battle.style.display    = 'none';
            if (victory) victory.style.display   = 'none';
            if (defeat)  defeat.style.display    = 'none';

            // FE-5 — Plan-5 dynamic boss arc kickoff. We race a 3 s timeout
            // against bossDynamicStart()+bossFetchNextQuestion() so a slow
            // server can't stall the boss forever. On any failure inside the
            // helpers, useDynamicBoss flips to false and we fall through to
            // the legacy initBossPlan() / BOSS_QUESTIONS[0] path below.
            // Wave F3 — boss-plan personalisation runs in parallel as a
            // legacy-mode fallback.
            // Sigma race-guard: kickoffExpired prevents a slow LLM response
            // (landing AFTER the 3s cap when the UI has already rendered
            // BOSS_QUESTIONS[0] in legacy mode) from silently writing to
            // bossState.currentQuestion / bossSessionId / useDynamicBoss=true.
            // Without this guard the student answers the legacy-rendered
            // question but the dynamic submit branch posts the (different)
            // server-generated question_id — cursed mirror grading.
            bossState.kickoffExpired = false;
            const planPromise = initBossPlan().catch(e => {
                console.warn('[F3] initBossPlan error:', e);
            });
            const dynamicReady = (async () => {
                if (!bossState.useDynamicBoss) {
                    return;
                }
                try {
                    await bossDynamicStart();
                    if (bossState.useDynamicBoss) {
                        await bossFetchNextQuestion();
                    }
                } catch (e) {
                    console.warn('[FE-5] dynamic kickoff threw, falling back:', e);
                    bossState.useDynamicBoss = false;
                }
            })();
            const timeoutPromise = new Promise(r => setTimeout(() => {
                bossState.kickoffExpired = true;
                if (!bossState.currentQuestion) {
                    bossState.useDynamicBoss = false;
                    console.warn('[FE-5] dynamic kickoff exceeded 3s, falling back to legacy');
                }
                r();
            }, 3000));
            const planReady = Promise.race([
                Promise.all([planPromise, dynamicReady]),
                timeoutPromise,
            ]);

            setTimeout(() => {
                if (intro) { intro.style.transition = 'opacity 500ms ease'; intro.style.opacity = '0'; }
                setTimeout(async () => {
                    if (intro) { intro.style.cssText = 'display:none;'; }
                    if (battle) battle.style.display = '';
                    bossUpdateHP(bossState.hp, false);
                    // Wait for the plan (or 3 s cap) before rendering Q0 so the
                    // first question always reflects the personalised order +
                    // framing rather than racing the intro animation.
                    await planReady;
                    bossRenderQuestion(0);
                    btn.classList.remove('state-line');
                    btn.classList.add('state-pill','pulse');
                    setBtnText(RT('btn.check_answer'));
                }, 520);
            }, 2400);
        }

        function bossNorm(s) {
            return s.toLowerCase()
                .replace(/\s+/g,'').replace(/[–—]/g,'-')
                .replace(/[''ʻʼ`]/g,"'").replace(/yo['']?q|yoq/g,'yoq')
                .replace(/x[₁₂12]/g,'x').replace(/haqiqiy/g,'haqiqiy');
        }

        // FB redesign — bossMatch removed. Server-only grading via bossSubmitAnswer.
        // BOSS_QUESTIONS no longer carries `acceptable[]` so a deterministic client
        // match would be impossible anyway. See _serialize_boss_questions in injector.

        // FB redesign — mint a session id for the boss arc + reset per-arc fields.
        // Called once on stage activation (start of boss). Idempotent.
        function bossInit() {
            const ctx = window.NETS_CTX || {};
            // Mint sessionId — random suffix + timestamp.
            const rand = Math.random().toString(36).slice(2, 10);
            bossState.sessionId = 'fb_' + Date.now() + '_' + rand;
            bossState.attemptsUsed = 0;
            bossState.outcome = null;
            bossState.stars = 0;
            bossState.outcomeXp = 0;
            bossState.busy = false;
            bossState.lastDamage = 0;
            bossState.damageDealt = 0;
            // BOSS_META override hooks.
            const meta = (typeof BOSS_META !== 'undefined' && BOSS_META) ? BOSS_META : null;
            if (meta && typeof meta.starting_hp_override === 'number' && meta.starting_hp_override >= 10) {
                bossState.maxHp = meta.starting_hp_override;
                bossState.hp = meta.starting_hp_override;
            }
            // Apply data-boss-type attribute for CSS hooks.
            const shell = document.getElementById('boss-shell');
            if (shell) {
                shell.setAttribute('data-boss-type', (meta && meta.boss_type) || 'sub');
            }
            bossUpdateAttemptPill();
            bossUpdateLowHpPulse();
        }

        // FE-5 — Plan 5 dynamic boss arc bootstrap. Mints a server-side
        // boss_session_id via NETS_AI.bossStart and mirrors the returned
        // hp/trials/difficulty into bossState. On any error/_offline/_error
        // we flip useDynamicBoss=false and fall back to the legacy
        // BOSS_QUESTIONS path so older homeworks keep rendering.
        async function bossDynamicStart() {
            if (!window.NETS_AI || typeof window.NETS_AI.bossStart !== 'function') {
                bossState.useDynamicBoss = false;
                return null;
            }
            const ctx = window.NETS_CTX || {};
            const sessionId = (typeof state !== 'undefined' && state.sessionId)
                ? state.sessionId
                : (localStorage.getItem('nets_tutor_session') || null);
            const hwId = ctx.hwId || ctx.homework_id || ctx.homeworkId
                || (typeof state !== 'undefined' && state.hwId) || null;
            try {
                const res = await window.NETS_AI.bossStart({
                    session_id: sessionId,
                    homework_id: hwId,
                    max_hp: bossState.maxHp,
                    trials_left: 7,
                });
                // Sigma race-guard: if the 3s startFinalBoss timeout already
                // expired while we were awaiting, abort silently — the UI is
                // (or is about to be) in legacy mode; do NOT clobber it.
                if (bossState.kickoffExpired) {
                    return null;
                }
                if (!res || res._error || res._offline || res._cap) {
                    console.warn('[FE-5] bossDynamicStart fell back to legacy:', res);
                    bossState.useDynamicBoss = false;
                    return null;
                }
                bossState.bossSessionId = res.boss_session_id || null;
                if (typeof res.max_hp === 'number' && res.max_hp >= 10) {
                    bossState.maxHp = res.max_hp;
                    bossState.hp = res.max_hp;
                }
                if (typeof res.trials_left === 'number') {
                    bossState.trialsLeft = res.trials_left;
                }
                if (res.current_difficulty) {
                    bossState.currentDifficulty = res.current_difficulty;
                }
                if (!bossState.bossSessionId) {
                    bossState.useDynamicBoss = false;
                    return null;
                }
                try { bossUpdateHP(bossState.hp, false); } catch (e) {}
                return res;
            } catch (err) {
                console.warn('[FE-5] bossDynamicStart threw, falling back:', err);
                bossState.useDynamicBoss = false;
                return null;
            }
        }

        // FE-5 — Pulls the next dynamic boss question from the server
        // (NETS_AI.bossGenerateQuestion). Whitelists the response per FE-6:
        // we render only question_id / question_text / target_skill /
        // difficulty / why_this_question. expected_answer / acceptable /
        // rubric / hints are explicitly stripped here even if the backend
        // ever leaks them — defense in depth. On failure we flip
        // useDynamicBoss=false so subsequent calls fall back to the legacy
        // BOSS_QUESTIONS index path.
        async function bossFetchNextQuestion() {
            if (!bossState.useDynamicBoss) return null;
            if (!window.NETS_AI || typeof window.NETS_AI.bossGenerateQuestion !== 'function') {
                bossState.useDynamicBoss = false;
                return null;
            }
            if (!bossState.bossSessionId) {
                bossState.useDynamicBoss = false;
                return null;
            }
            try {
                const res = await window.NETS_AI.bossGenerateQuestion({
                    boss_session_id: bossState.bossSessionId,
                    recent_boss_phrases: bossState.recentBossPhrases.slice(-5),
                });
                // Sigma race-guard: if the 3s startFinalBoss timeout already
                // expired while we were awaiting, abort silently. Writing
                // currentQuestion now would clobber the legacy-mode UI the
                // student is already looking at and produce mirror-grading.
                if (bossState.kickoffExpired) {
                    return null;
                }
                if (!res || res._error || res._offline || res._cap) {
                    console.warn('[FE-5] bossFetchNextQuestion fell back to legacy:', res);
                    bossState.useDynamicBoss = false;
                    return null;
                }
                // Whitelist — strip expected_answer / acceptable / rubric /
                // hints if backend ever leaks them. Frontend never renders them.
                const safe = {
                    question_id: res.question_id || null,
                    question_text: res.question_text || '',
                    target_skill: res.target_skill || '',
                    difficulty: res.difficulty || bossState.currentDifficulty || '',
                    why_this_question: res.why_this_question || '',
                };
                // Defense in depth: explicitly drop the forbidden fields.
                // (No-op if absent; just guarantees nothing leaks downstream.)
                delete safe.expected_answer;
                delete safe.acceptable;
                delete safe.rubric;
                delete safe.hints;
                bossState.currentQuestion = safe;
                if (res.difficulty) bossState.currentDifficulty = res.difficulty;
                // Track a short snippet for anti-repetition (cap at 5 entries).
                const snippet = (safe.question_text || '').split(/\s+/).slice(0, 8).join(' ');
                if (snippet) {
                    bossState.recentBossPhrases.push(snippet);
                    if (bossState.recentBossPhrases.length > 5) {
                        bossState.recentBossPhrases.shift();
                    }
                }
                return safe;
            } catch (err) {
                console.warn('[FE-5] bossFetchNextQuestion threw, falling back:', err);
                bossState.useDynamicBoss = false;
                return null;
            }
        }

        // FB redesign — single network swap-point. Mirrors gbTMCheckPair / rlcCheckStep.
        // Reads ctx.hwId FIRST per TM #140 / SF lesson, then snake_case alternates.
        // FE-5 — branches on bossState.useDynamicBoss: dynamic path goes through
        // window.NETS_AI.bossSubmitAnswer (Plan 5 endpoint), legacy path keeps
        // the /api/ai/check-answer fetch so older homework templates keep working.
        async function bossSubmitAnswer(questionId, studentAnswer, attemptNumber) {
            // FE-5 dynamic branch — Plan 5 boss arc.
            if (bossState.useDynamicBoss && bossState.bossSessionId
                && window.NETS_AI && typeof window.NETS_AI.bossSubmitAnswer === 'function') {
                try {
                    const res = await window.NETS_AI.bossSubmitAnswer({
                        boss_session_id: bossState.bossSessionId,
                        question_id: questionId,
                        student_answer: studentAnswer,
                    });
                    if (!res || res._error || res._offline || res._cap) {
                        console.warn('[FE-5] bossSubmitAnswer (dynamic) failed:', res);
                        return null;
                    }
                    return res;
                } catch (err) {
                    console.warn('[FE-5] bossSubmitAnswer (dynamic) threw:', err);
                    return null;
                }
            }
            // Legacy branch — pre-Plan-5 contract via /api/ai/check-answer.
            const ctx = window.NETS_CTX || {};
            const meta = (typeof BOSS_META !== 'undefined' && BOSS_META) ? BOSS_META : null;
            try {
                const res = await fetch('/api/ai/check-answer', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        phase: 'final-boss',
                        homework_id: ctx.hwId || ctx.homework_id || ctx.homeworkId || null,
                        question_id: questionId,
                        student_answer: studentAnswer,
                        attempt_number: attemptNumber,
                        session_id: bossState.sessionId,
                        boss_type: (meta && meta.boss_type) || 'sub',
                        grade_band: (meta && meta.grade_band) || null,
                        hp_remaining: bossState.hp,
                        attempts_used: bossState.attemptsUsed || 0,
                    }),
                });
                if (!res.ok) return null;
                return await res.json();
            } catch (err) {
                console.warn('[FB] bossSubmitAnswer failed:', err);
                return null;
            }
        }

        // FB redesign — server-driven response handler. Replaces local match logic.
        // FE-5 — accepts both Plan-5 (`is_correct`, `trials_left`,
        // `current_difficulty`, `feedback`) and legacy (`correct`,
        // `boss_response`) shapes. Plan-5 takes precedence when present.
        function bossHandleResponse(resp, q, fbEl) {
            if (!resp) {
                if (fbEl) { fbEl.className = 'boss-feedback wrong'; fbEl.textContent = RT('boss.toast.wrong'); }
                bossImpactFlash();
                return;
            }
            // FE-5: prefer resp.is_correct (Plan-5), fall back to resp.correct (legacy).
            const isCorrect = (resp.is_correct === true) || (resp.correct === true);
            // Mirror server-side counters when present.
            if (typeof resp.attempts_used === 'number') {
                bossState.attemptsUsed = resp.attempts_used;
            }
            // FE-5 — mirror Plan-5 trials_left + current_difficulty.
            if (typeof resp.trials_left === 'number') {
                bossState.trialsLeft = resp.trials_left;
            }
            if (resp.current_difficulty) {
                bossState.currentDifficulty = resp.current_difficulty;
            }
            if (isCorrect) {
                // Use server values for damage + HP (no client recompute).
                const serverDamage = (typeof resp.damage_dealt === 'number') ? resp.damage_dealt : null;
                const serverHp = (typeof resp.hp_remaining === 'number') ? resp.hp_remaining : null;
                bossApplyCorrect(q, fbEl, {
                    aiGraded: true,
                    axis_1: resp.axis_1,
                    axis_2: resp.axis_2,
                });
                // Bug FB-1 fix: damageDealt was double-counting. bossApplyCorrect
                // already added the local `dmg` to bossState.damageDealt; if the
                // server returns its own authoritative damage, we previously
                // added serverDamage on top, doubling the total shown on the
                // result card. Subtract bossState.lastDamage (= the local dmg
                // bossApplyCorrect just accumulated) before adding serverDamage
                // so the server value is the single source of truth when present.
                if (serverDamage !== null) {
                    bossState.damageDealt -= bossState.lastDamage;
                    bossState.lastDamage = serverDamage;
                    bossState.damageDealt += serverDamage;
                }
                if (serverHp !== null) {
                    bossState.hp = Math.max(0, serverHp);
                    bossUpdateHP(bossState.hp, true);
                }
                bossUpdateLowHpPulse();
            } else {
                bossState.combo = 0;
                bossUpdateCombo();
                bossState.attemptsUsed = (bossState.attemptsUsed || 0) + 1;
                bossImpactFlash();
                if (fbEl) {
                    fbEl.className = 'boss-feedback wrong';
                    // FE-5 — Plan-5 returns `feedback`; legacy returns `boss_response`.
                    const aiMsg = resp.feedback || resp.boss_response || RT('boss.toast.wrong');
                    // Sigma XSS guard: aiMsg is LLM-generated. textContent +
                    // programmatic span instead of innerHTML so a malicious
                    // (or hallucinated) feedback string can't inject script.
                    fbEl.textContent = aiMsg + ' ';
                    const badge = document.createElement('span');
                    badge.className = 'screen-reading-ai-badge';
                    badge.textContent = 'AI baho';
                    fbEl.appendChild(badge);
                }
                bossUpdateAttemptPill();
                // Log incorrect attempt to AMR session log (mirrors legacy nets:result handler shape).
                if (window.__sessionLog) {
                    window.__sessionLog.push({
                        phase: 'final-boss', id: q.id || ('boss-' + (bossState.qIndex + 1)),
                        correct: false, score: typeof resp.score === 'number' ? resp.score : 0,
                        axis_1: resp.axis_1 || 1, axis_2: resp.axis_2 || 1,
                        first_try: false, damage: 0,
                    });
                }
            }
            // Done branch — server signals end-of-boss.
            if (resp.done === true) {
                bossRenderResult(resp);
            }
        }

        // FB redesign — red impact flash overlay + screen shake on wrong submit.
        function bossImpactFlash() {
            const flash = document.getElementById('boss-impact-flash');
            if (flash) {
                flash.classList.remove('show');
                void flash.offsetHeight;
                flash.classList.add('show');
                setTimeout(() => { flash.classList.remove('show'); }, 380);
            }
            const card = document.getElementById('boss-card');
            if (card) {
                card.classList.remove('shake');
                void card.offsetHeight;
                card.classList.add('shake');
                setTimeout(() => { card.classList.remove('shake'); }, 460);
            }
        }

        // FB redesign — amber heal flash overlay on hint use (server returns hp cost).
        function bossHealFlash(hpRegainedAmount) {
            const flash = document.getElementById('boss-heal-flash');
            if (flash) {
                flash.classList.remove('show');
                void flash.offsetHeight;
                flash.classList.add('show');
                setTimeout(() => { flash.classList.remove('show'); }, 380);
            }
            const fb = document.getElementById('boss-feedback');
            if (fb && typeof hpRegainedAmount === 'number') {
                const msg = RT('boss.hint_used_amber').replace('{n}', String(hpRegainedAmount));
                fb.className = 'boss-feedback';
                fb.textContent = msg;
                setTimeout(() => { if (fb && fb.textContent === msg) fb.textContent = ''; }, 1800);
            }
        }

        // FB redesign — toggle .low-hp on .boss-card when HP <= 25%.
        function bossUpdateLowHpPulse() {
            const card = document.getElementById('boss-card');
            if (!card) return;
            const ratio = bossState.maxHp > 0 ? (bossState.hp / bossState.maxHp) : 0;
            if (ratio <= 0.25 && ratio > 0) {
                card.classList.add('low-hp');
            } else {
                card.classList.remove('low-hp');
            }
            // Also annotate the HP bar for gradient bias.
            const bar = document.getElementById('boss-hp-bar');
            if (bar) {
                if (ratio <= 0.25) bar.setAttribute('data-hp-pct', 'low');
                else if (ratio <= 0.55) bar.setAttribute('data-hp-pct', 'mid');
                else bar.removeAttribute('data-hp-pct');
            }
        }

        // FB redesign — sticky attempt pill ("Urinish 1/2") for boss_type=sub w/ attempts_max set.
        function bossUpdateAttemptPill() {
            const pill = document.getElementById('boss-attempt-pill');
            if (!pill) return;
            const meta = (typeof BOSS_META !== 'undefined' && BOSS_META) ? BOSS_META : null;
            const bossType = (meta && meta.boss_type) || 'sub';
            const attemptsMax = meta ? meta.attempts_max : null;
            // Mythical: forced attempts_max=1 per spec §3 — pill HIDDEN (single-shot, no UI affordance for "retry").
            if (bossType === 'mythical') {
                pill.style.display = 'none';
                return;
            }
            // Big or premium-unlimited: hide unless explicit cap.
            if (!attemptsMax || attemptsMax < 2) {
                pill.style.display = 'none';
                return;
            }
            const used = (bossState.attemptsUsed || 0);
            const current = Math.min(used + 1, attemptsMax);
            pill.style.display = '';
            pill.textContent = RT('boss.attempt_of')
                .replace('{n}', String(current))
                .replace('{max}', String(attemptsMax));
        }

        // FB redesign — render result card on server-signaled `done`. Calls completePhase('boss').
        function bossRenderResult(resp) {
            // Bug FB-2 fix: arm bossState.done so the guard at the top of
            // bossHandleAction (`if (state.isAnimating || bossState.done) return;`)
            // actually fires post-result. Without this, qIndex would keep
            // incrementing on subsequent clicks and bossEnd(false) would be
            // called even though the student WON the boss. Set early so it
            // applies even if any of the DOM lookups below short-circuit.
            bossState.done = true;
            bossState.outcome = resp && resp.outcome ? resp.outcome : 'passing';
            bossState.stars = (resp && typeof resp.stars === 'number') ? resp.stars : 0;
            bossState.outcomeXp = (resp && typeof resp.outcome_xp === 'number') ? resp.outcome_xp : 0;
            const card = document.getElementById('boss-result-card');
            if (!card) {
                // Fallback: just continue to existing flow.
                completePhase('boss');
                return;
            }
            const titleEl = document.getElementById('boss-result-title');
            const starsEl = document.getElementById('boss-result-stars');
            const xpEl = document.getElementById('boss-result-xp');
            const sumEl = document.getElementById('boss-result-summary');
            if (titleEl) titleEl.textContent = RT('boss.outcome.' + bossState.outcome);
            if (starsEl) {
                starsEl.innerHTML = '';
                for (let i = 1; i <= 3; i++) {
                    const span = document.createElement('span');
                    span.className = 'boss-star ' + (i <= bossState.stars ? 'earned' : 'dim');
                    span.textContent = '★';
                    starsEl.appendChild(span);
                }
            }
            if (xpEl) {
                xpEl.textContent = RT('boss.result.xp').replace('{n}', String(bossState.outcomeXp));
            }
            if (sumEl) {
                // FE-5 — dynamic mode counts attempted questions (qIndex+1) since
                // the server controls arc length and there's no fixed BOSS_QUESTIONS
                // total; legacy mode keeps the original BOSS_QUESTIONS.length.
                let total;
                if (bossState.useDynamicBoss) {
                    total = Math.max(bossState.correct || 0, (bossState.qIndex || 0) + 1);
                } else {
                    total = (typeof BOSS_QUESTIONS !== 'undefined' && Array.isArray(BOSS_QUESTIONS))
                        ? BOSS_QUESTIONS.length : 0;
                }
                sumEl.textContent = RT('boss.result.summary')
                    .replace('{correct}', String(bossState.correct || 0))
                    .replace('{total}', String(total))
                    .replace('{damage}', String(bossState.damageDealt || 0))
                    .replace('{hints}', String(bossState.hintsUsed || 0));
            }
            card.style.display = '';
            // Force reflow then add .show for transition.
            void card.offsetHeight;
            card.classList.add('show');
            // Mark phase complete (replaces direct bossEnd path on done).
            try { completePhase('boss'); } catch (e) {}
        }

        function bossRenderQuestion(idx) {
            const el = (id) => document.getElementById(id);
            // FE-5 — dynamic branch reads from bossState.currentQuestion (server-supplied,
            // whitelisted in bossFetchNextQuestion). Legacy branch keeps reading
            // BOSS_QUESTIONS[idx] so older homework templates still render.
            if (bossState.useDynamicBoss && bossState.currentQuestion) {
                const dq = bossState.currentQuestion;
                // Hide legacy framing banner (Plan-4 personalisation doesn't apply
                // to the Plan-5 dynamic loop — server-side prompt drives tone).
                const framingEl = el('boss-framing');
                if (framingEl) { framingEl.textContent = ''; framingEl.style.display = 'none'; }
                // Sigma XSS guard: dq.question_text is LLM-generated. Use
                // textContent (never innerHTML) so server output can never
                // inject script/markup. Legacy branch below keeps innerHTML
                // for q.prompt because BOSS_QUESTIONS is server-injected
                // STATIC content (inline <img>/<svg>/bold), not LLM text.
                if (el('boss-q-text'))    el('boss-q-text').textContent    = dq.question_text || '';
                if (el('boss-q-tags')) {
                    const parts = [];
                    if (dq.target_skill) parts.push(dq.target_skill);
                    if (dq.difficulty) parts.push(dq.difficulty);
                    let tagText = parts.length ? ('[' + parts.join(' · ') + ']') : '';
                    if (dq.why_this_question) {
                        tagText = tagText ? (tagText + ' — ' + dq.why_this_question) : dq.why_this_question;
                    }
                    el('boss-q-tags').textContent = tagText;
                }
                if (el('boss-q-counter')) {
                    let counterText = RT('boss.question_of') + ' ' + (idx + 1);
                    if (typeof bossState.trialsLeft === 'number') {
                        counterText += ' · ' + bossState.trialsLeft;
                    }
                    el('boss-q-counter').textContent = counterText;
                }
                const inp = el('boss-input');
                if (inp) { inp.value = ''; inp.disabled = false; inp.style.borderColor = ''; }
                // FE-5 — hint flow is disabled in dynamic mode (server-driven prompts;
                // hints aren't part of the Plan-5 contract).
                if (el('boss-hint-text')) {
                    el('boss-hint-text').textContent = '';
                    el('boss-hint-text').style.display = 'none';
                }
                const hb = el('boss-hint-btn');
                if (hb) {
                    if (bossState.useDynamicBoss) { hb.disabled = true; hb.style.display = 'none'; }
                    else { hb.disabled = false; hb.style.display = ''; }
                }
                const fb = el('boss-feedback'); if (fb) { fb.className = 'boss-feedback'; fb.textContent = ''; }
                bossState.answered = false;
                bossState.hintStep = 0;
                bossUpdateCombo();
                return;
            }
            // Legacy branch — pre-Plan-5 BOSS_QUESTIONS rendering (preserved).
            const q = BOSS_QUESTIONS[idx];
            // Wave F3 — personalized framing banner (purely additive; stems untouched).
            const framingEl = el('boss-framing');
            if (framingEl) {
                const framing = q._framing || '';
                if (framing) {
                    framingEl.textContent = framing;
                    framingEl.style.display = '';
                } else {
                    framingEl.textContent = '';
                    framingEl.style.display = 'none';
                }
            }
            // innerHTML — boss question may contain inline images/SVGs/bold/italic.
            if (el('boss-q-text'))    el('boss-q-text').innerHTML      = q.prompt || '';
            if (el('boss-q-tags'))    el('boss-q-tags').textContent    = '[Bloom: ' + q.bloom + ' | PISA: ' + q.pisa + ']';
            if (el('boss-q-counter')) el('boss-q-counter').textContent = RT('boss.question_of') + ' ' + (idx+1) + ' / ' + BOSS_QUESTIONS.length;
            const inp = el('boss-input');
            if (inp) { inp.value = ''; inp.disabled = false; inp.style.borderColor = ''; }
            if (el('boss-hint-text')) el('boss-hint-text').textContent = '';
            const hb = el('boss-hint-btn'); if (hb) hb.disabled = false;
            const fb = el('boss-feedback'); if (fb) { fb.className = 'boss-feedback'; fb.textContent = ''; }
            bossState.answered = false;
            bossState.hintStep = 0;
            bossUpdateCombo();
        }

        // Tracks the currently-pending boss AI lookup so a stale response from a
        // previous question can't overwrite the current question's UI.
        let bossPendingAi = null;

        function bossApplyCorrect(q, fbEl, opts) {
            // opts: { aiGraded: bool, message: string|null, axis_1?, axis_2? }
            bossState.correct++;
            bossState.combo++;
            const doubled = bossState.combo >= 3;
            // FE-5 — in dynamic mode q.damage is undefined; default to 0 here.
            // bossHandleResponse mirrors the authoritative resp.damage_dealt /
            // resp.hp_remaining values from the server immediately after this
            // function returns (subtracting bossState.lastDamage to avoid the
            // double-count fixed by FB-1).
            const baseDamage = (q && typeof q.damage === 'number') ? q.damage : 0;
            const dmg = doubled ? baseDamage * 2 : baseDamage;
            bossState.hp = Math.max(0, bossState.hp - dmg);
            bossState.lastDamage = dmg;
            bossState.damageDealt = (bossState.damageDealt || 0) + dmg;
            bossUpdateHP(bossState.hp, true);
            bossUpdateCombo();
            // FB redesign — refresh low-HP pulse on every HP delta.
            try { bossUpdateLowHpPulse(); } catch (e) {}
            if (fbEl) {
                fbEl.className = 'boss-feedback correct';
                const baseMsg = doubled ? (RT('boss.combo_hp') + dmg + ' HP') : (RT('boss.correct_hp') + dmg + ' HP');
                if (opts && opts.aiGraded) {
                    // Sigma XSS guard: even though baseMsg is composed from
                    // RT() locale strings + numeric dmg, we mirror the
                    // textContent + programmatic-badge pattern from
                    // bossHandleResponse so future edits to baseMsg can't
                    // accidentally interpolate untrusted server text into
                    // an innerHTML sink.
                    fbEl.textContent = baseMsg + ' ';
                    const badge = document.createElement('span');
                    badge.className = 'screen-reading-ai-badge';
                    badge.textContent = 'AI baho';
                    fbEl.appendChild(badge);
                } else {
                    fbEl.textContent = baseMsg;
                }
            }
            // Log boss attack outcome for the AMR scorecard.
            // Per GRADING.md: only AI-graded open responses contribute to AMR
            // axis means. Closed-form correct items count toward damage and
            // the donut/phase tally but their axes are intentionally omitted.
            if (window.__sessionLog) {
                const entry = {
                    phase: 'final-boss', id: q.id || ('boss-' + (bossState.qIndex + 1)),
                    correct: true, score: 1,
                    first_try: !(opts && opts.aiGraded),
                    damage: dmg,
                };
                if (opts && opts.aiGraded && typeof opts.axis_1 === 'number' && typeof opts.axis_2 === 'number') {
                    entry.axis_1 = opts.axis_1;
                    entry.axis_2 = opts.axis_2;
                } else {
                    entry.closed = true;
                }
                window.__sessionLog.push(entry);
            }
            if (bossState.hp <= 0) { setTimeout(() => bossEnd(true), 900); }
        }

        // FB redesign — async + server-only grading via bossSubmitAnswer.
        async function bossHandleAction() {
            if (state.isAnimating) return;
            // Bug FB-2 fix: when bossState.done is true (server-signaled
            // end-of-boss; result card is showing) clicking the action
            // button must route forward to the same downstream phase that
            // bossEnd(victory) uses — setStage(7.5) → showResultsScreen
            // (per L17134-17141). Previously this branch silently returned,
            // dead-ending the student on the boss-result card with a
            // looking-but-not-working Next button. We mirror bossEnd's
            // navigation rather than calling bossEnd(false) so a victorious
            // student isn't mislabeled as defeated.
            if (bossState.done) {
                if (typeof setStage === 'function') setStage(7.5);
                if (typeof showResultsScreen === 'function') {
                    showResultsScreen();
                }
                return;
            }

            if (bossState.answered) {
                bossState.qIndex++;
                // FE-5 — dynamic mode: fetch the next server-generated question.
                // The server signals end-of-arc via resp.done in bossRenderResult,
                // so there is NO BOSS_QUESTIONS.length boundary here — we just
                // pull the next question and render it. If the fetch fails the
                // helper flips useDynamicBoss=false and we fall through to the
                // legacy index path.
                if (bossState.useDynamicBoss) {
                    setPhaseProgress('boss', bossState.qIndex, bossState.qIndex + 1);
                    await bossFetchNextQuestion();
                    if (!bossState.useDynamicBoss) {
                        // Fetch failed; fall back into legacy path.
                        if (bossState.qIndex >= BOSS_QUESTIONS.length) { bossEnd(false); return; }
                    }
                    bossRenderQuestion(bossState.qIndex);
                    setBtnText(RT('btn.check_answer'));
                    return;
                }
                // Legacy mode — index into BOSS_QUESTIONS.
                setPhaseProgress('boss', bossState.qIndex, BOSS_QUESTIONS.length);
                if (bossState.qIndex >= BOSS_QUESTIONS.length) { bossEnd(false); return; }
                bossRenderQuestion(bossState.qIndex);
                setBtnText(RT('btn.check_answer'));
                return;
            }

            const inp = document.getElementById('boss-input');
            const val = inp ? inp.value.trim() : '';
            if (!val) {
                if (inp) { inp.style.borderColor = '#d9534f'; setTimeout(() => { inp.style.borderColor = ''; }, 1200); }
                return;
            }
            if (bossState.busy) return; // Concurrency gate (mirrors TM/RLC).

            // FE-5 — dynamic question carries question_id from server; legacy uses BOSS_QUESTIONS[idx].id.
            const q = (bossState.useDynamicBoss && bossState.currentQuestion)
                ? bossState.currentQuestion
                : BOSS_QUESTIONS[bossState.qIndex];
            const questionId = q ? (q.question_id || q.id) : null;
            const fb = document.getElementById('boss-feedback');
            if (inp) inp.disabled = true;
            // Loading state while we await the server. Pre-fix code reused
            // the red `.boss-feedback.wrong` class with text `✗ Noto'g'ri.
            // AI tahlil qilmoqda...` here — that pre-empts the verdict
            // before the AI has decided. Now use the neutral blue
            // `.boss-feedback.loading` (with spinner glyph) and a clean
            // "Tekshirilmoqda…" message; the wrong branch only fires in
            // bossHandleResponse() AFTER the AI confirms wrong.
            if (fb) { fb.className = 'boss-feedback loading'; fb.textContent = RT('boss.checking'); }

            bossState.busy = true;
            const attemptNumber = (bossState.attemptsUsed || 0) + 1;
            const resp = await bossSubmitAnswer(questionId, val, attemptNumber);
            bossState.busy = false;

            // Fail-soft: null response means network/HTTP error — keep wrong state, allow retry.
            if (!resp) {
                if (fb) { fb.className = 'boss-feedback wrong'; fb.textContent = RT('boss.toast.wrong'); }
                if (inp) inp.disabled = false;
                bossImpactFlash();
                return;
            }
            bossState.answered = true;
            bossHandleResponse(resp, q, fb);

            setBtnText(RT('btn.next_question'));
        }

        function bossUseHint() {
            if (bossState.answered) return;
            // FE-5 — hints are not part of the Plan-5 dynamic boss contract.
            // Hint button is hidden in bossRenderQuestion's dynamic branch;
            // belt-and-suspenders early exit here in case it's reached anyway.
            if (bossState.useDynamicBoss) return;
            const q = BOSS_QUESTIONS[bossState.qIndex];
            if (!q || !Array.isArray(q.hints)) return;
            if (bossState.hintStep >= q.hints.length) return;
            const hint = q.hints[bossState.hintStep++];
            bossState.hintsUsed++;
            bossState.combo = 0;
            bossUpdateCombo();
            const hpBefore = bossState.hp;
            bossState.hp = Math.min(bossState.maxHp, bossState.hp + 10);
            bossUpdateHP(bossState.hp, false);
            try { bossUpdateLowHpPulse(); } catch (e) {}
            // FB redesign — visual heal flash + amber message (server-driven cost
            // wired in bossHandleResponse for the new path; this legacy path keeps +10).
            try { bossHealFlash(bossState.hp - hpBefore); } catch (e) {}
            const ht = document.getElementById('boss-hint-text');
            const hb = document.getElementById('boss-hint-btn');
            if (ht) ht.textContent = '💡 ' + hint;
            if (hb && bossState.hintStep >= q.hints.length) hb.disabled = true;
        }

        function bossUpdateHP(hp, animate) {
            const bar = document.getElementById('boss-hp-bar');
            const num = document.getElementById('boss-hp-num');
            const pct = Math.max(0, (hp / bossState.maxHp) * 100);
            if (bar) {
                bar.style.width = pct + '%';
                pct === 0 ? bar.classList.add('empty') : bar.classList.remove('empty');
                if (animate) { bar.classList.remove('shake'); void bar.offsetHeight; bar.classList.add('shake'); setTimeout(() => bar.classList.remove('shake'), 440); }
            }
            if (num) num.textContent = Math.max(0, Math.round(hp)) + ' HP';
        }

        function bossUpdateCombo() {
            const el = document.getElementById('boss-combo');
            if (!el) return;
            if (bossState.combo >= 3)      { el.textContent = RT('boss.combo_x2'); el.classList.add('active'); }
            else if (bossState.combo >= 2) { el.textContent = '⚡ ' + bossState.combo + ' ' + RT('boss.combo_streak'); el.classList.add('active'); }
            else                           { el.classList.remove('active'); }
        }

        function bossEnd(victory) {
            // Direct boss → results flow.
            // Per UX: there is NO intermediate victory/defeat splash and NO
            // reflection interstitial between the last attack and the AMR
            // scorecard. The student finishes the boss and immediately sees
            // their score; the conditional Tugatish / Qayta bajarish button
            // at the bottom of the scorecard owns the next-step decision.
            bossState.done = true;
            // Boss phase fully done — student finished or HP hit 0.
            completePhase('boss');
            const battle = document.getElementById('boss-battle');
            if (battle) { battle.style.transition = 'opacity 400ms ease'; battle.style.opacity = '0'; }

            // Make absolutely sure the legacy victory / defeat splash cards
            // stay hidden — older builds toggled them on here.
            const vEl = document.getElementById('boss-victory'); if (vEl) vEl.style.display = 'none';
            const dEl = document.getElementById('boss-defeat');  if (dEl) dEl.style.display = 'none';

            setTimeout(() => {
                if (battle) { battle.style.display = 'none'; battle.style.opacity = ''; battle.style.transition = ''; }
                // Flush the morphing button — the scorecard's own footer
                // button takes over from here.
                if (typeof btn !== 'undefined' && btn) {
                    btn.classList.remove('pulse', 'state-pill');
                    btn.classList.add('state-line');
                    if (typeof btnText !== 'undefined' && btnText) btnText.style.opacity = '0';
                }
                // Jump straight to results, skipping reflection too — per
                // GRADING.md §7 reflection is participation-only and not
                // part of the score, so it has no business between the
                // final attack and the scorecard.
                setStage(7.5);
                if (typeof showResultsScreen === 'function') {
                    showResultsScreen();
                } else {
                    // Defensive — should never trigger, but if for some reason
                    // the function isn't injected, just clear the screen.
                    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
                }
            }, 440);
        }

        /* ── WAVE 2 · READING / CONSOLIDATION / REFLECTION ──────────────────
           These three phases live in content_json.{reading,consolidation,reflection}.
           The injector replaces the placeholder objects below with author content.
           Empty objects → renderers auto-skip the screen so legacy fixtures don't
           show blank pages. */

        const READING = {
            title: "",
            passage: "",
            checkpoints: []
        };

        const CONSOLIDATION = {
            title: "",
            mnemonic: "",
            bullets: [],
            check_prompt: "",
            check_answer: "",
            recap: ""
        };

        const REFLECTION = {
            summary: "",
            question: "",
            spaced_rep: "",
            closing: ""
        };

        // Listening (graded): audio + gated transcript + checkpoints. The
        // injector stamps content_json.listening here. Empty → auto-skips.
        const LISTENING = {
            title: "",
            audio_url: "",
            transcript: "",
            checkpoints: []
        };

        // Extra Materials (ungraded): supplementary links/videos. Empty → skips.
        const EXTRA_MATERIALS = {
            title: "",
            intro: "",
            items: []
        };

        function readingHasContent() {
            if (!READING) return false;
            const has = ((READING.passage || READING.text) && String(READING.passage || READING.text).trim()) ||
                        (READING.title && String(READING.title).trim()) ||
                        (Array.isArray(READING.checkpoints) && READING.checkpoints.length);
            return Boolean(has);
        }

        function consolidationHasContent() {
            if (!CONSOLIDATION) return false;
            const has = (CONSOLIDATION.mnemonic && String(CONSOLIDATION.mnemonic).trim()) ||
                        (CONSOLIDATION.recap && String(CONSOLIDATION.recap).trim()) ||
                        (Array.isArray(CONSOLIDATION.bullets) && CONSOLIDATION.bullets.length) ||
                        (CONSOLIDATION.check_prompt && String(CONSOLIDATION.check_prompt).trim());
            return Boolean(has);
        }

        function reflectionHasContent() {
            if (!REFLECTION) return false;
            const has = (REFLECTION.summary && String(REFLECTION.summary).trim()) ||
                        (REFLECTION.question && String(REFLECTION.question).trim()) ||
                        (REFLECTION.spaced_rep && String(REFLECTION.spaced_rep).trim()) ||
                        (REFLECTION.closing && String(REFLECTION.closing).trim());
            return Boolean(has);
        }

        function listeningHasContent() {
            if (!LISTENING) return false;
            const has = (LISTENING.audio_url && String(LISTENING.audio_url).trim()) ||
                        (LISTENING.transcript && String(LISTENING.transcript).trim()) ||
                        (Array.isArray(LISTENING.checkpoints) && LISTENING.checkpoints.length);
            return Boolean(has);
        }

        function extraMaterialsHasContent() {
            if (!EXTRA_MATERIALS) return false;
            return Boolean(Array.isArray(EXTRA_MATERIALS.items) && EXTRA_MATERIALS.items.length);
        }

        function readingNorm(s) {
            return String(s || '').trim().toLowerCase()
                .replace(/\s+/g, ' ')
                .replace(/[''ʻʼ`]/g, "'")
                .replace(/[–—]/g, '-');
        }

        function readingMatchLocal(studentVal, cp) {
            const norm = readingNorm(studentVal);
            if (!norm) return false;
            const candidates = [];
            if (cp.ans) candidates.push(cp.ans);
            if (Array.isArray(cp.acceptable)) candidates.push(...cp.acceptable);
            return candidates.some(a => readingNorm(a) === norm);
        }

        const readingState = {
            page: 0,
            pages: [],
            answered: [],
            answers: [],
            results: [],
            feedback: [],
            onContinue: null,
        };

        function readingEscapeHtml(value) {
            return String(value == null ? '' : value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function readingTextFromHtml(html) {
            const div = document.createElement('div');
            div.innerHTML = String(html || '');
            return (div.textContent || div.innerText || '').trim();
        }

        function readingBuildPages(rawPassage, segments) {
            // New segment-aware path: explicit segments[] from content_json.
            // When a segment carries a checkpoint, emit ONE combined page that
            // shows the passage text on top with the question + input + check
            // button + feedback area directly below it. When the segment has
            // no checkpoint, emit a text-only page (legacy behavior).
            if (Array.isArray(segments) && segments.length) {
                const pages = [];
                segments.forEach((seg, i) => {
                    const segText = (seg && (seg.text || seg.html)) ? String(seg.text || seg.html) : '';
                    const hasCheckpoint = !!(seg && seg.checkpoint);
                    if (hasCheckpoint) {
                        pages.push({ kind: 'segment_with_question', html: segText, cpIndex: i });
                    } else {
                        pages.push({ kind: 'text', html: segText });
                    }
                });
                return pages;
            }
            // Legacy chunker fallback: passage as one HTML blob, checkpoints get
            // geometrically attached to chunked pages at render time. Old fixtures
            // (no segments[] in content_json) keep working unchanged.
            const raw = String(rawPassage || '').trim();
            if (!raw) return [];
            let chunks;
            const paragraphMatches = raw.match(/<p\b[\s\S]*?<\/p>/gi);
            if (paragraphMatches && paragraphMatches.length > 1) {
                chunks = paragraphMatches;
            } else {
                const text = readingTextFromHtml(raw) || raw.replace(/<br\s*\/?>/gi, ' ').replace(/<[^>]*>/g, ' ');
                const sentences = (text.match(/[^.!?]+[.!?]+(?:["')\]]+)?|[^.!?]+$/g) || [text])
                    .map(s => s.trim())
                    .filter(Boolean);
                chunks = [];
                let current = [];
                let length = 0;
                sentences.forEach(sentence => {
                    const nextLength = length + sentence.length;
                    if (current.length && (current.length >= 2 || nextLength > 260)) {
                        chunks.push(current.join(' '));
                        current = [];
                        length = 0;
                    }
                    current.push(sentence);
                    length += sentence.length;
                });
                if (current.length) chunks.push(current.join(' '));
                chunks = chunks.map(chunk => '<p>' + readingEscapeHtml(chunk) + '</p>');
            }
            return chunks.map(html => ({ kind: 'legacy', html }));
        }

        function readingCheckpointPage(index, totalPages, checkpointCount) {
            if (!checkpointCount) return -1;
            return Math.min(totalPages - 1, Math.max(0, Math.round(((index + 1) * totalPages) / checkpointCount) - 1));
        }

        function readingIsComplete(checkpoints) {
            if (!checkpoints.length) return true;
            return checkpoints.every((_, i) => Boolean(readingState.answered[i]));
        }

        function updateReadingContinueState() {
            const checkpoints = Array.isArray(READING.checkpoints) ? READING.checkpoints : [];
            const done = readingIsComplete(checkpoints);
            const status = document.getElementById('reading-status');

            // Lock-message scoping: "Davom etish uchun savolga javob bering" should
            // appear ONLY on a question panel that's still unanswered. Text-only
            // segment panels and the all-done state both hide it. Legacy chunker
            // pages show it when the page has any unanswered geometric checkpoint.
            let pageNeedsAnswer = false;
            const currentPage = readingState.pages[readingState.page] || { kind: 'text' };
            if ((currentPage.kind === 'question' || currentPage.kind === 'segment_with_question')
                && typeof currentPage.cpIndex === 'number') {
                pageNeedsAnswer = !readingState.answered[currentPage.cpIndex];
            } else if (currentPage.kind === 'legacy') {
                const idxs = checkpoints
                    .map((_, i) => i)
                    .filter(i => readingCheckpointPage(i, readingState.pages.length, checkpoints.length) === readingState.page);
                pageNeedsAnswer = idxs.some(i => !readingState.answered[i]);
            }
            if (status) {
                if (pageNeedsAnswer) {
                    status.textContent = RT('reading.must_answer');
                    status.style.display = '';
                } else if (done) {
                    status.textContent = RT('reading.all_done');
                    status.style.display = '';
                } else {
                    status.textContent = '';
                    status.style.display = 'none';
                }
            }

            if (!btn) return;
            btn.classList.remove('pulse', 'state-pill', 'state-line');
            if (done) {
                btn.classList.add('state-pill', 'pulse');
            } else {
                btn.classList.add('state-line');
            }
            setBtnText(RT('btn.continue'));
        }

        // Thin wrapper kept for compat with finishReading's `firstMissing` jump.
        // Real navigation goes through the wave2 slide stream.
        function readingGoToPage(nextPage) {
            const max = Math.max(0, readingState.pages.length - 1);
            readingState.page = Math.min(max, Math.max(0, nextPage));
            wave2SlideTo('reading-stream', readingState.page);
        }

        // Build one .wave2-slide-page for a checkpoint question. Mode: 'segment'
        // (auto-advance on correct, no manual Next) or 'legacy' (manual Next,
        // no auto-advance — preserves old chunker UX for pre-segment fixtures).
        function _buildReadingCheckpointBlock(i, cp, mode, readingPassage) {
            cp = cp || {};
            const block = document.createElement('div');
            block.className = 'screen-reading-checkpoint';
            block.id = 'reading-cp-' + i;

            const q = document.createElement('div');
            q.className = 'screen-reading-prompt';
            q.innerHTML = '<span class="caption screen-reading-q-tag">Q' + (i + 1) + '</span>' + (cp.prompt || cp.q || '');
            block.appendChild(q);

            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'screen-reading-input';
            input.id = 'reading-cp-input-' + i;
            input.setAttribute('autocomplete', 'off');
            input.setAttribute('autocapitalize', 'off');
            input.setAttribute('spellcheck', 'false');
            input.placeholder = RT('reading.placeholder');
            input.value = readingState.answers[i] || '';
            input.disabled = Boolean(readingState.answered[i]);
            block.appendChild(input);

            const btnRow = document.createElement('div');
            btnRow.className = 'screen-reading-btn-row';
            const checkBtn = document.createElement('button');
            checkBtn.type = 'button';
            checkBtn.className = 'screen-reading-btn';
            checkBtn.id = 'reading-cp-check-' + i;
            checkBtn.textContent = RT('reading.check');
            checkBtn.disabled = Boolean(readingState.answered[i]);
            btnRow.appendChild(checkBtn);

            // Manual Next button:
            //   - Legacy mode: always present, hidden until any answer is
            //     submitted (preserves pre-segment UX).
            //   - Segment mode: present but only revealed when the student
            //     answered INCORRECTLY. Correct answers auto-advance after
            //     1.1s (see check handler below); the wrong-answer branch
            //     used to leave the student stuck with no advance affordance
            //     other than the page dots — this is the escape hatch.
            const nextBtn = document.createElement('button');
            nextBtn.type = 'button';
            nextBtn.className = 'screen-reading-btn is-primary';
            nextBtn.id = 'reading-cp-next-' + i;
            nextBtn.textContent = RT('btn.next');
            const shouldShowInitially = readingState.answered[i] && (
                mode === 'legacy' || readingState.results[i] === false
            );
            nextBtn.style.display = shouldShowInitially ? '' : 'none';
            btnRow.appendChild(nextBtn);
            block.appendChild(btnRow);

            const fb = document.createElement('div');
            fb.className = 'screen-reading-feedback';
            fb.id = 'reading-cp-fb-' + i;
            if (readingState.feedback[i]) {
                fb.style.display = '';
                fb.className = 'screen-reading-feedback ' + (readingState.results[i] ? 'is-correct' : 'is-wrong');
                fb.innerHTML = readingState.feedback[i];
            } else {
                fb.style.display = 'none';
            }
            block.appendChild(fb);

            checkBtn.addEventListener('click', async () => {
                if (input.disabled) return;
                const studentAnswer = (input.value || '').trim();
                if (!studentAnswer) {
                    input.style.borderColor = '#d9534f';
                    setTimeout(() => { input.style.borderColor = ''; }, 1200);
                    return;
                }
                const isLanguage = (typeof gbIsLanguageSubject === 'function')
                    ? gbIsLanguageSubject() : false;
                const expectedList = [];
                if (cp.ans) expectedList.push(cp.ans);
                if (Array.isArray(cp.acceptable)) expectedList.push(...cp.acceptable);
                input.disabled = true;
                checkBtn.disabled = true;
                let isCorrect;
                let aiResult = null;
                if (isLanguage) {
                    fb.style.display = '';
                    fb.className = 'screen-reading-feedback is-pending';
                    fb.innerHTML = '<em>' + RT('wc.checking') + '</em>';
                    try {
                        const resp = await fetch('/api/ai/check-answer', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                question_id: cp.id || ('reading-cp-' + i),
                                question: cp.prompt || cp.q || '',
                                student_answer: studentAnswer,
                                expected_answers: expectedList,
                                answer_spec: {
                                    type: 'semantic',
                                    expected: (expectedList[0] || ''),
                                    canonical_display: (expectedList[0] || ''),
                                    allow_ai_fallback: true,
                                    amr: true,
                                },
                                allow_ai_fallback: true,
                                subject: (window.NETS_CTX && NETS_CTX.subject) || 'english',
                                grade: (window.NETS_CTX && NETS_CTX.grade) || 8,
                                tier: 'HARD',
                                phase: 'reading-checkpoint',
                                context: readingPassage,
                            }),
                        });
                        if (resp.ok) aiResult = await resp.json();
                    } catch (e) { /* fall back to local match */ }
                    isCorrect = (aiResult && typeof aiResult.correct === 'boolean')
                        ? aiResult.correct
                        : readingMatchLocal(studentAnswer, cp);
                } else {
                    isCorrect = readingMatchLocal(studentAnswer, cp);
                }
                fb.style.display = '';
                if (isCorrect) {
                    fb.className = 'screen-reading-feedback is-correct';
                    const aiFb = (aiResult && aiResult.feedback) ? (' <span style="opacity:0.85;">' + aiResult.feedback + '</span>') : '';
                    const cpFb = cp.fb ? (' <span style="opacity:0.85;">' + cp.fb + '</span>') : '';
                    fb.innerHTML = RT('reading.correct') + aiFb + cpFb;
                } else {
                    fb.className = 'screen-reading-feedback is-wrong';
                    const expected = cp.ans ? ('<br><span style="opacity:0.85;">' + RT('reading.right_answer') + ' ' + cp.ans + '</span>') : '';
                    const aiFb = (aiResult && aiResult.feedback) ? ('<br><span style="opacity:0.7;">' + aiResult.feedback + '</span>') : '';
                    const cpFb = cp.fb ? ('<br><span style="opacity:0.7;">' + cp.fb + '</span>') : '';
                    fb.innerHTML = RT('reading.wrong') + expected + aiFb + cpFb;
                }
                readingState.answered[i] = true;
                readingState.answers[i] = studentAnswer;
                readingState.results[i] = Boolean(isCorrect);
                readingState.feedback[i] = fb.innerHTML;
                // Reveal manual Next when there's no auto-advance:
                //   - legacy mode: always (current behavior preserved)
                //   - segment mode + wrong answer: escape hatch — auto-advance
                //     only fires on correct, so without this the student is
                //     stuck on a wrong-answer panel with no visible advancer.
                if (mode === 'legacy' || !isCorrect) {
                    nextBtn.style.display = '';
                }
                updateReadingContinueState();

                // Segment-aware mode: auto-advance after correct via the wave2
                // helper. Legacy chunker mode keeps the manual Next button so
                // pre-segment fixtures don't change UX behavior.
                if (isCorrect && mode === 'segment') {
                    setTimeout(() => {
                        wave2SlideNavigate('reading-stream', +1);
                    }, 1100);
                }

                if (window.__sessionLog) {
                    const entry = {
                        phase: 'reading-checkpoint',
                        id: cp.id || ('reading-cp-' + i),
                        correct: isCorrect,
                        score: (aiResult && typeof aiResult.score === 'number') ? aiResult.score : (isCorrect ? 1 : 0),
                    };
                    if (aiResult && typeof aiResult.axis_1 === 'number') entry.axis_1 = aiResult.axis_1;
                    if (aiResult && typeof aiResult.axis_2 === 'number') entry.axis_2 = aiResult.axis_2;
                    window.__sessionLog.push(entry);
                }
            });

            nextBtn.addEventListener('click', () => {
                if (!readingState.answered[i]) return;
                wave2SlideNavigate('reading-stream', +1);
            });

            return block;
        }

        function renderReading() {
            const titleEl = document.getElementById('reading-title');
            const stream = document.getElementById('reading-stream');
            const progressEl = document.getElementById('reading-progress');
            const checkpoints = Array.isArray(READING.checkpoints) ? READING.checkpoints : [];
            const segments = Array.isArray(READING.segments) ? READING.segments : null;
            const readingPassage = READING.passage || READING.text || '';

            if (titleEl) titleEl.textContent = (READING.title || RT('reading.title_default')).toUpperCase();
            readingState.pages = readingBuildPages(readingPassage, segments);
            if (!readingState.pages.length) readingState.pages = [{ kind: 'text', html: '' }];
            readingState.page = 0;

            if (!stream) return;
            stream.innerHTML = '';

            // One wave2-slide-page per logical reading panel. Text segments
            // render their HTML; question panels render the checkpoint UI;
            // legacy chunker pages combine text + any geometric checkpoint(s).
            readingState.pages.forEach((page, idx) => {
                const panelEl = document.createElement('div');
                panelEl.className = 'wave2-slide-page';
                panelEl.dataset.pageKind = page.kind;
                panelEl.dataset.pageIndex = String(idx);

                if (page.kind === 'text') {
                    const passage = document.createElement('div');
                    passage.className = 'screen-reading-passage';
                    passage.innerHTML = page.html || '';
                    panelEl.appendChild(passage);
                } else if (page.kind === 'segment_with_question') {
                    // Combined page: passage text on top, checkpoint UI below
                    // — same .wave2-slide-page wraps both. Calls into the
                    // existing _buildReadingCheckpointBlock to avoid duplicating
                    // the question/input/feedback logic.
                    const cpIdx = page.cpIndex;
                    const passage = document.createElement('div');
                    passage.className = 'screen-reading-passage';
                    passage.innerHTML = page.html || '';
                    panelEl.appendChild(passage);
                    panelEl.appendChild(_buildReadingCheckpointBlock(cpIdx, checkpoints[cpIdx], 'segment', readingPassage));
                } else if (page.kind === 'question') {
                    const cpIdx = page.cpIndex;
                    panelEl.appendChild(_buildReadingCheckpointBlock(cpIdx, checkpoints[cpIdx], 'segment', readingPassage));
                } else { // 'legacy'
                    const passage = document.createElement('div');
                    passage.className = 'screen-reading-passage';
                    passage.innerHTML = page.html || '';
                    panelEl.appendChild(passage);
                    const attachedCps = checkpoints
                        .map((_, i) => i)
                        .filter(i => readingCheckpointPage(i, readingState.pages.length, checkpoints.length) === idx);
                    attachedCps.forEach(cpIdx => {
                        panelEl.appendChild(_buildReadingCheckpointBlock(cpIdx, checkpoints[cpIdx], 'legacy', readingPassage));
                    });
                }

                stream.appendChild(panelEl);
            });

            wave2SlideInit({
                containerId: 'reading-stream',
                dotsId: 'reading-dots',
                panelCount: readingState.pages.length,
                canAdvance: (fromIdx, toIdx) => {
                    // Back-swipe always allowed.
                    if (toIdx < fromIdx) return true;
                    const fromPage = readingState.pages[fromIdx] || { kind: 'text' };
                    if ((fromPage.kind === 'question' || fromPage.kind === 'segment_with_question')
                        && typeof fromPage.cpIndex === 'number') {
                        if (!readingState.answered[fromPage.cpIndex]) {
                            updateReadingContinueState();
                            return false;
                        }
                    } else if (fromPage.kind === 'legacy') {
                        const idxs = checkpoints
                            .map((_, i) => i)
                            .filter(i => readingCheckpointPage(i, readingState.pages.length, checkpoints.length) === fromIdx);
                        if (idxs.some(i => !readingState.answered[i])) {
                            updateReadingContinueState();
                            return false;
                        }
                    }
                    return true;
                },
                onSettle: (idx) => {
                    readingState.page = idx;
                    if (progressEl) {
                        progressEl.textContent = RT('reading.page_label') + ' ' + (idx + 1) + ' / ' + readingState.pages.length;
                    }
                    updateReadingContinueState();
                    const card = document.getElementById('reading-content-card');
                    if (card) card.scrollTop = 0;
                },
                onExitForward: () => {
                    if (readingIsComplete(checkpoints) && typeof readingState.onContinue === 'function') {
                        readingState.onContinue();
                    }
                },
                onExitBackward: () => { /* no phase before reading inside the wave2 stream */ },
            });

            if (progressEl) {
                progressEl.textContent = RT('reading.page_label') + ' 1 / ' + readingState.pages.length;
            }
            updateReadingContinueState();
        }

        const consState = { onContinue: null };

        function renderConsolidation() {
            const titleEl = document.getElementById('cons-title');
            if (titleEl) titleEl.textContent = (CONSOLIDATION.title || RT('cons.title_default')).toUpperCase();

            const stream = document.getElementById('cons-stream');
            const dotsRow = document.getElementById('cons-dots');
            const legacyBlock = document.getElementById('cons-legacy-block');
            const panels = Array.isArray(CONSOLIDATION.panels) ? CONSOLIDATION.panels : null;

            if (panels && panels.length) {
                // ── Bug #7: panels[] shape — sliding panel sequence ──────────
                if (legacyBlock) legacyBlock.style.display = 'none';
                if (stream) stream.style.display = '';
                if (dotsRow) dotsRow.style.display = '';

                if (!stream) return;
                stream.innerHTML = '';
                panels.forEach((p, i) => {
                    const panelEl = document.createElement('div');
                    panelEl.className = 'wave2-slide-page';
                    panelEl.dataset.panelKind = p.kind || '';
                    panelEl.dataset.panelIndex = String(i);

                    if (p.media && p.media.html) {
                        const mediaEl = document.createElement('div');
                        mediaEl.className = 'cons-panel-media';
                        mediaEl.innerHTML = p.media.html;
                        panelEl.appendChild(mediaEl);
                    }
                    if (p.title) {
                        const h = document.createElement('h3');
                        h.className = 'cons-panel-title';
                        h.innerHTML = p.title;
                        panelEl.appendChild(h);
                    }
                    if (p.html) {
                        const body = document.createElement('div');
                        body.className = 'cons-panel-body content-area';
                        body.innerHTML = p.html;
                        panelEl.appendChild(body);
                    }

                    // The 'check' kind panel (or any panel marked check) carries
                    // the reveal-on-demand block. Not graded — student clicks
                    // "Show answer" to expose it. No advance gating.
                    if (p.kind === 'check' && CONSOLIDATION.check) {
                        const checkBlock = document.createElement('div');
                        checkBlock.className = 'cons-panel-check';
                        const prompt = document.createElement('div');
                        prompt.className = 'screen-cons-prompt content-area';
                        prompt.innerHTML = CONSOLIDATION.check.prompt || '';
                        checkBlock.appendChild(prompt);
                        const toggle = document.createElement('button');
                        toggle.type = 'button';
                        toggle.className = 'screen-cons-toggle';
                        toggle.textContent = RT('cons.show_answer');
                        checkBlock.appendChild(toggle);
                        const answerEl = document.createElement('div');
                        answerEl.className = 'screen-cons-answer content-area';
                        answerEl.innerHTML = CONSOLIDATION.check.answer
                            ? (RT('cons.expected_prefix') + CONSOLIDATION.check.answer)
                            : '';
                        checkBlock.appendChild(answerEl);
                        toggle.addEventListener('click', () => {
                            if (toggle.disabled) return;
                            toggle.disabled = true;
                            answerEl.classList.add('is-revealed');
                        });
                        panelEl.appendChild(checkBlock);
                    }

                    stream.appendChild(panelEl);
                });

                wave2SlideInit({
                    containerId: 'cons-stream',
                    dotsId: 'cons-dots',
                    panelCount: panels.length,
                    canAdvance: () => true, // not graded — never block navigation
                    onSettle: () => {
                        const card = document.getElementById('cons-card');
                        if (card) card.scrollTop = 0;
                    },
                    onExitForward: () => {
                        if (typeof consState.onContinue === 'function') consState.onContinue();
                    },
                    onExitBackward: () => { /* no phase before consolidation in the stream */ },
                });
                return;
            }

            // ── Legacy shape — single scrollable card ─────────────────────────
            if (stream) stream.style.display = 'none';
            if (dotsRow) dotsRow.style.display = 'none';
            if (legacyBlock) legacyBlock.style.display = '';

            const mn = document.getElementById('cons-mnemonic');
            if (mn) mn.innerHTML = CONSOLIDATION.mnemonic || CONSOLIDATION.recap || '';
            const bl = document.getElementById('cons-bullets');
            if (bl) {
                bl.innerHTML = '';
                const bullets = Array.isArray(CONSOLIDATION.bullets) ? CONSOLIDATION.bullets : [];
                bullets.forEach(b => {
                    const li = document.createElement('li');
                    li.innerHTML = b || '';
                    bl.appendChild(li);
                });
            }
            const checkBlock = document.getElementById('cons-check-block');
            const cp = document.getElementById('cons-check-prompt');
            const ca = document.getElementById('cons-check-answer');
            const toggle = document.getElementById('cons-check-toggle');
            const hasCheck = Boolean((CONSOLIDATION.check_prompt && String(CONSOLIDATION.check_prompt).trim()));
            if (checkBlock) checkBlock.style.display = hasCheck ? '' : 'none';
            if (cp) cp.innerHTML = CONSOLIDATION.check_prompt || '';
            if (ca) {
                ca.innerHTML = CONSOLIDATION.check_answer ? (RT('cons.expected_prefix') + CONSOLIDATION.check_answer) : '';
                ca.classList.remove('is-revealed');
            }
            if (toggle) {
                const hasAnswer = Boolean((CONSOLIDATION.check_answer && String(CONSOLIDATION.check_answer).trim()));
                toggle.style.display = hasAnswer ? '' : 'none';
                toggle.disabled = false;
                toggle.textContent = RT('cons.show_answer');
                const fresh = toggle.cloneNode(true);
                toggle.parentNode.replaceChild(fresh, toggle);
                fresh.addEventListener('click', () => {
                    if (fresh.disabled) return;
                    fresh.disabled = true;
                    if (ca) {
                        ca.classList.add('is-revealed');
                        try { ca.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) { /* ignore */ }
                    }
                });
            }

            // Dedicated fallback — the shared #action-button stays in state-line
            // (invisible 4px bar) if playPhaseAnnouncement's callback never fires.
            const nextBtn = document.getElementById('cons-next-btn');
            if (nextBtn) {
                nextBtn.textContent = RT('btn.next_page');
                const fresh = nextBtn.cloneNode(true);
                nextBtn.parentNode.replaceChild(fresh, nextBtn);
                fresh.addEventListener('click', () => {
                    if (typeof consState.onContinue === 'function') consState.onContinue();
                });
            }
        }

        function renderReflection() {
            const s = document.getElementById('ref-summary');
            const q = document.getElementById('ref-question');
            const sr = document.getElementById('ref-spaced-rep');
            const c = document.getElementById('ref-closing');
            if (s) s.innerHTML = REFLECTION.summary || '';
            if (q) q.innerHTML = REFLECTION.question || '';
            if (sr) sr.innerHTML = REFLECTION.spaced_rep || '';
            if (c) c.innerHTML = REFLECTION.closing || '';
        }

        // Wave 2 stage values — see phaseMap comment near setStage for the
        // half-step convention. Reading sits between MS-end (4.5) and game
        // breaks (5); consolidation between real-life (6) and boss (7);
        // reflection after boss-done (7.5) before the finish state.
        // ── Listening (graded: audio + gated transcript + checkpoints) ─────
        // Mirrors Reading but the source is audio. The "one rule": the
        // transcript stays locked until the student has played the audio.
        // Checkpoint grading reuses readingMatchLocal() and logs a
        // 'listening-checkpoint' entry to the AMR session log, so it is graded.
        const listeningState = { played: false, results: [], onContinue: null };

        function listeningEscAttr(s) {
            return String(s || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;');
        }

        function listeningAllCorrect() {
            const cps = Array.isArray(LISTENING.checkpoints) ? LISTENING.checkpoints : [];
            if (!cps.length) return true;
            return cps.every((_, i) => listeningState.results[i]);
        }

        function listeningUpdateContinue() {
            if (listeningAllCorrect() && listeningState.onContinue) {
                btn.classList.remove('state-line');
                btn.classList.add('state-pill', 'pulse');
                setBtnText(RT('btn.continue'));
                if (btnText) btnText.style.opacity = '';
            }
        }

        function renderListening() {
            const titleEl = document.getElementById('listening-title');
            if (titleEl) titleEl.textContent = (LISTENING.title || 'Tinglash').toUpperCase();
            const body = document.getElementById('listening-body');
            if (!body) return;
            const cps = Array.isArray(LISTENING.checkpoints) ? LISTENING.checkpoints : [];
            listeningState.results = cps.map(() => false);
            const audioUrl = String(LISTENING.audio_url || '').trim();
            const transcript = String(LISTENING.transcript || '').trim();

            let html = '';
            if (audioUrl) {
                html += '<audio id="listening-audio" class="listening-audio" controls preload="none" src="'
                      + listeningEscAttr(audioUrl) + '"></audio>';
            }
            if (transcript) {
                html += '<div class="listening-transcript-wrap">'
                      +   '<button type="button" id="listening-transcript-btn" class="screen-cons-toggle"'
                      +     (audioUrl ? ' disabled' : '') + '>Transkriptni ko\'rsatish</button>'
                      +   '<div id="listening-transcript-hint" class="screen-reading-status"'
                      +     (audioUrl ? '' : ' style="display:none;"') + '>Transkript audioni tinglagandan so\'ng ochiladi.</div>'
                      +   '<div id="listening-transcript" class="content-area" style="display:none;">' + transcript + '</div>'
                      + '</div>';
            }
            cps.forEach((cp, i) => {
                html += '<div class="listening-cp editor-card" data-cp="' + i + '">'
                      +   '<div class="content-area">' + (cp.prompt || ('Savol ' + (i + 1))) + '</div>'
                      +   '<input type="text" class="listening-cp-input" data-cp="' + i + '" placeholder="Javobingiz" />'
                      +   '<button type="button" class="listening-cp-check screen-cons-toggle" data-cp="' + i + '">Tekshirish</button>'
                      +   '<div class="listening-cp-fb" data-cp="' + i + '" style="display:none;"></div>'
                      + '</div>';
            });
            body.innerHTML = html;

            // Gated transcript — unlock the reveal button only after the audio
            // has actually started playing (the "one rule"). With no audio
            // authored, the transcript is available immediately.
            const audioEl = document.getElementById('listening-audio');
            const tBtn = document.getElementById('listening-transcript-btn');
            const tHint = document.getElementById('listening-transcript-hint');
            if (audioEl) {
                audioEl.addEventListener('play', () => {
                    listeningState.played = true;
                    if (tBtn) tBtn.disabled = false;
                    if (tHint) tHint.style.display = 'none';
                }, { once: true });
            }
            if (tBtn) {
                tBtn.addEventListener('click', () => {
                    if (tBtn.disabled) return;
                    const t = document.getElementById('listening-transcript');
                    if (!t) return;
                    const open = t.style.display !== 'none';
                    t.style.display = open ? 'none' : '';
                    tBtn.textContent = open ? 'Transkriptni ko\'rsatish' : 'Transkriptni yashirish';
                });
            }

            body.addEventListener('click', (e) => {
                const checkBtn = e.target.closest('.listening-cp-check');
                if (!checkBtn) return;
                const i = Number(checkBtn.dataset.cp);
                const cp = cps[i];
                const input = body.querySelector('.listening-cp-input[data-cp="' + i + '"]');
                const fb = body.querySelector('.listening-cp-fb[data-cp="' + i + '"]');
                const val = input ? input.value : '';
                if (!String(val).trim()) {
                    if (input) { input.style.borderColor = '#d9534f'; setTimeout(() => { input.style.borderColor = ''; }, 1200); }
                    return;
                }
                const ok = readingMatchLocal(val, cp);
                const already = listeningState.results[i];
                listeningState.results[i] = ok;
                if (fb) {
                    fb.style.display = '';
                    fb.className = 'listening-cp-fb ' + (ok ? 'is-correct' : 'is-wrong');
                    fb.innerHTML = ok ? (cp.fb || 'To\'g\'ri ✓') : 'Qayta urinib ko\'ring.';
                }
                if (ok) {
                    if (input) input.disabled = true;
                    checkBtn.disabled = true;
                }
                // Log once per checkpoint (first correct answer) so the AMR
                // scorecard counts Listening like any other graded phase.
                if (ok && !already && window.__sessionLog) {
                    window.__sessionLog.push({
                        phase: 'listening-checkpoint',
                        id: cp.id || ('listening-cp-' + i),
                        correct: true,
                        score: 1,
                    });
                }
                listeningUpdateContinue();
            });

            listeningUpdateContinue();
        }

        function showListeningScreen(onContinue) {
            if (!listeningHasContent()) { onContinue(); return; }
            listeningState.played = false;
            setStage(4.8);
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            const sl = document.getElementById('screen-listening');
            if (sl) sl.classList.add('active');
            listeningState.onContinue = onContinue;
            const handler = () => {
                // Graded: only advance once every checkpoint is answered correctly.
                if (!listeningAllCorrect()) return;
                btn.removeEventListener('click', handler, true);
                if (sl) sl.classList.remove('active');
                onContinue();
            };
            btn.classList.remove('pulse', 'state-pill', 'tm-dock-hidden');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            renderListening();
            btn.addEventListener('click', handler, true);
        }

        // ── Extra Materials (ungraded supplementary links/videos) ──────────
        function extraEscText(s) {
            return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function extraSafeUrl(u) {
            const v = String(u || '').trim();
            return /^(https?:|mailto:)/i.test(v) ? v : '';
        }

        function renderExtraMaterials() {
            const titleEl = document.getElementById('extra-title');
            if (titleEl) titleEl.textContent = (EXTRA_MATERIALS.title || 'Qo\'shimcha materiallar').toUpperCase();
            const body = document.getElementById('extra-body');
            if (!body) return;
            const items = Array.isArray(EXTRA_MATERIALS.items) ? EXTRA_MATERIALS.items : [];
            const intro = String(EXTRA_MATERIALS.intro || '').trim();
            let html = '';
            if (intro) html += '<div class="content-area extra-intro">' + intro + '</div>';
            html += '<ul class="extra-materials-list">';
            items.forEach((it) => {
                const url = extraSafeUrl(it.url);
                if (!url) return;
                const label = String(it.label || '').trim() || url;
                const kind = String(it.kind || '').trim().toLowerCase();
                const icon = kind === 'video' ? '🎬' : (kind === 'file' ? '📎' : (kind === 'article' ? '📄' : '🔗'));
                html += '<li class="extra-materials-item">'
                      +   '<a href="' + listeningEscAttr(url) + '" target="_blank" rel="noopener noreferrer">'
                      +     '<span class="extra-icon" aria-hidden="true">' + icon + '</span> '
                      +     extraEscText(label)
                      +   '</a>'
                      + '</li>';
            });
            html += '</ul>';
            body.innerHTML = html;
        }

        function showExtraMaterialsScreen(onContinue) {
            if (!extraMaterialsHasContent()) { onContinue(); return; }
            setStage(7.6);
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            const se = document.getElementById('screen-extra');
            if (se) se.classList.add('active');
            renderExtraMaterials();
            const handler = () => {
                btn.removeEventListener('click', handler, true);
                if (se) se.classList.remove('active');
                onContinue();
            };
            // Ungraded → the continue button is available immediately.
            btn.classList.remove('state-line', 'tm-dock-hidden');
            btn.classList.add('state-pill', 'pulse');
            setBtnText(RT('btn.continue'));
            if (btnText) btnText.style.opacity = '';
            btn.addEventListener('click', handler, true);
        }

        function showReadingScreen(onContinue) {
            if (!readingHasContent()) { onContinue(); return; }
            readingState.page = 0;
            readingState.pages = [];
            readingState.answered = [];
            readingState.answers = [];
            readingState.results = [];
            readingState.feedback = [];
            setStage(4.7);
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            const sr = document.getElementById('screen-reading');
            if (sr) sr.classList.add('active');
            const finishReading = (force) => {
                const checkpoints = Array.isArray(READING.checkpoints) ? READING.checkpoints : [];
                // `force` lets the edge-swipe phase-skip gesture exit the reading
                // phase even when checkpoints are unanswered. The within-phase
                // continue button + auto-advance both call without `force` so the
                // checkpoint lock still gates normal navigation.
                if (!force && !readingIsComplete(checkpoints)) {
                    updateReadingContinueState();
                    const firstMissing = checkpoints.findIndex((_, i) => !readingState.answered[i]);
                    if (firstMissing >= 0) {
                        // Segment-aware: jump to that checkpoint's question panel.
                        // Legacy: fall back to geometric checkpoint→page mapping.
                        const targetPage = readingState.pages.findIndex(p =>
                            p && p.kind === 'question' && p.cpIndex === firstMissing
                        );
                        readingGoToPage(targetPage >= 0
                            ? targetPage
                            : readingCheckpointPage(firstMissing, readingState.pages.length, checkpoints.length));
                    }
                    return;
                }
                btn.removeEventListener('click', handler, true);
                if (sr) sr.classList.remove('active');
                onContinue();
            };
            readingState.onContinue = finishReading;
            // Hide the reading content card during the intro announcement.
            const readingContent = document.getElementById('reading-content-card');
            if (readingContent) { readingContent.style.transition = 'none'; readingContent.style.opacity = '0'; }
            // Keep button inert during the intro.
            btn.classList.remove('pulse','state-pill');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            playPhaseIntro('reading-phase-center-card', () => {
                if (readingContent) { readingContent.style.transition = 'opacity 300ms ease'; readingContent.style.opacity = '1'; }
                renderReading();
                btn.addEventListener('click', handler, true);
            });
            function handler() { finishReading(); }
        }

        function showConsolidationScreen(onContinue) {
            if (!consolidationHasContent()) { onContinue(); return; }
            setStage(6.5);
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            const sc = document.getElementById('screen-consolidation');
            if (sc) sc.classList.add('active');
            renderConsolidation();
            // Bug #4: hold content + button inert during phase announcement.
            // Also strip `tm-dock-hidden` defensively — Tile Match's dock-hide
            // class can leak across phases when the GB exit path bypasses
            // gbSetButtonNext (the helper that normally auto-clears it).
            if (sc) { sc.style.transition = 'none'; sc.style.opacity = '0'; }
            btn.classList.remove('pulse', 'state-pill', 'state-line', 'tm-dock-hidden');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            const handler = () => {
                btn.removeEventListener('click', handler, true);
                if (sc) sc.classList.remove('active');
                onContinue();
            };
            // Bug #7: store onContinue on consState so the wave2 stream's
            // onExitForward (swipe past last panel) can trigger phase exit
            // without the bottom button. The bottom button still works as a
            // fallback for legacy single-card mode + as a backup for the
            // sliding mode if the user prefers tapping it.
            consState.onContinue = () => {
                btn.removeEventListener('click', handler, true);
                if (sc) sc.classList.remove('active');
                onContinue();
            };
            playPhaseAnnouncement('phase.consolidation', () => {
                if (sc) { sc.style.transition = 'opacity 300ms ease'; sc.style.opacity = '1'; }
                btn.classList.remove('state-line');
                btn.classList.add('state-pill', 'pulse');
                setBtnText(RT('btn.continue'));
                if (btnText) btnText.style.opacity = '';
                btn.addEventListener('click', handler, true);
            });
        }

        function showReflectionScreen(onContinue) {
            if (!reflectionHasContent()) { onContinue(); return; }
            setStage(7.7);
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            const sr = document.getElementById('screen-reflection');
            if (sr) sr.classList.add('active');
            renderReflection();
            // Bug #4: hold content + button inert during phase announcement.
            if (sr) { sr.style.transition = 'none'; sr.style.opacity = '0'; }
            btn.classList.remove('pulse', 'state-pill', 'state-line');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            const handler = () => {
                btn.removeEventListener('click', handler, true);
                if (sr) sr.classList.remove('active');
                onContinue();
            };
            playPhaseAnnouncement('phase.reflection', () => {
                if (sr) { sr.style.transition = 'opacity 300ms ease'; sr.style.opacity = '1'; }
                btn.classList.remove('state-line');
                btn.classList.add('state-pill', 'pulse');
                setBtnText(RT('btn.finish'));
                if (btnText) btnText.style.opacity = '';
                btn.addEventListener('click', handler, true);
            });
        }

        /* ── Stage 9 · AMR Results Scorecard ──────────────────────────
           The TEMPLATE NO LONGER COMPUTES THE SCORE. It collects the
           session log into window.__sessionLog as the student plays,
           then POSTs the log to /api/grading/aggregate and renders the
           scorecard from the backend response.

           The grading rules — which phase uses which method, the score
           formula `((axis_1 + axis_2) / 2) * 25`, band thresholds, the
           60% conditional-button rule — all live in
           `server/services/grading.py`. Adding a new game = update the
           PHASE_METHOD dict there. This template is just a renderer.

           See: D:/Class A Education/standards/framework/GRADING.md
        */

        // Initialize the session log as early as the script runs so
        // every phase's grading handler can write to it without checking.
        if (!window.__sessionLog) window.__sessionLog = [];

        // Render one AMR axis bar from the backend's prepared shape:
        //   { mean: number|null, perf_class: string, tag: string }
        function _renderAxisBar(label, axis) {
            if (!axis || axis.mean == null) {
                return `<div class="results-axis">
                  <div class="results-axis-label">${label}</div>
                  <div class="results-axis-value">—</div>
                  <div class="results-axis-bar-wrap">
                    <div class="results-axis-bar is-empty"></div>
                    <div class="results-axis-ticks"><span>1</span><span>2</span><span>3</span><span>4</span></div>
                  </div>
                  <div class="results-axis-tag perf-neutral">${(axis && axis.tag) || ''}</div>
                </div>`;
            }
            const mean = Number(axis.mean);
            const x = Math.max(0, Math.min(100, ((mean - 1) / 3) * 100));
            return `<div class="results-axis">
              <div class="results-axis-label">${label}</div>
              <div class="results-axis-value">${mean.toFixed(2)} / 4</div>
              <div class="results-axis-bar-wrap">
                <div class="results-axis-bar"></div>
                <div class="results-axis-marker" style="left:${x.toFixed(2)}%"></div>
                <div class="results-axis-ticks"><span>1</span><span>2</span><span>3</span><span>4</span></div>
              </div>
              <div class="results-axis-tag ${axis.perf_class}">${axis.tag}</div>
            </div>`;
        }

        // Fetch the scorecard payload from the backend.
        // Falls back to a minimal local synthesis if the network call
        // fails — the student should never be left without a score —
        // but the canonical compute path is the server.
        async function _fetchScorecard(log) {
            try {
                // Wave J / T4: forward homework_failed + warning_deductions
                // (set by the tutor widget when its state machine triggers).
                // Backend grading service applies the deduction AFTER AMR
                // and clamps the final score to 0 when failed.
                const body = {
                    items: log,
                    homework_id: (window.NETS_CTX && window.NETS_CTX.homework_id) || null,
                    // Subject is forwarded so the backend picks the right
                    // axis labels (LMR for language subjects, AMR otherwise).
                    subject: (window.NETS_CTX && window.NETS_CTX.subject) || null,
                };
                // Skipped-question penalty: tell the backend the total open
                // count so dismissing questions no longer inflates the mean
                // over answered ones. Counts every question that COULD have
                // produced AMR/LMR axes if it had been answered.
                try {
                    let expected = 0;
                    // Real-Life q1..qN
                    if (typeof RL_SCENARIO !== 'undefined' && RL_SCENARIO &&
                        Array.isArray(RL_SCENARIO.questions)) {
                        expected += RL_SCENARIO.questions.length;
                    }
                    // Final Boss attacks
                    if (typeof BOSS_QUESTIONS !== 'undefined' &&
                        Array.isArray(BOSS_QUESTIONS)) {
                        expected += BOSS_QUESTIONS.length;
                    }
                    // Reading checkpoints (LMR-only path)
                    if (typeof READING !== 'undefined' && READING &&
                        Array.isArray(READING.checkpoints)) {
                        expected += READING.checkpoints.length;
                    }
                    if (expected > 0) body.expected_open_count = expected;
                } catch (_) { /* best-effort — backend defaults are safe */ }
                if (window.__homeworkFailed) body.homework_failed = true;
                if (typeof window.__warningDeductions === 'number'
                    && window.__warningDeductions > 0) {
                    body.warning_deductions = window.__warningDeductions;
                }
                const resp = await fetch('/api/grading/aggregate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (!resp.ok) throw new Error('http ' + resp.status);
                return await resp.json();
            } catch (e) {
                console.warn('[scorecard] backend aggregate failed, using minimal fallback:', e.message);
                // Minimal fallback — counts correct/total only, no axes.
                let c = 0, t = 0;
                for (const x of log) {
                    if (x && typeof x === 'object') {
                        t += 1;
                        if (x.correct) c += 1;
                    }
                }
                const pct = t > 0 ? Math.round(100 * c / t) : 0;
                const perf_class = pct >= 75 ? 'perf-good' : (pct >= 50 ? 'perf-mid' : 'perf-bad');
                const action_label = pct >= 60 ? 'Tugatish' : 'Qayta bajarish';
                const action_kind  = pct >= 60 ? 'finish'    : 'redo';
                return {
                    overall_pct: pct, overall_score: null, has_axes: false,
                    band: { key: 'novice', name: 'Novice' }, perf_class,
                    overall_axis_1: null, overall_axis_2: null,
                    phases: [], totals: { correct: c, items: t },
                    axes: { axis_1: { mean: null, perf_class: 'perf-neutral', tag: '' },
                            axis_2: { mean: null, perf_class: 'perf-neutral', tag: '' } },
                    coaching_tip: 'Backend ishlamadi — vaqtinchalik mahalliy hisob.',
                    action: { kind: action_kind, label: action_label, perf_class: action_kind === 'finish' ? 'is-finish' : 'is-redo' },
                };
            }
        }

        // ── Wave J / T4: tutor-failed → jump to reflection ────────
        // The tutor widget IIFE dispatches `nets:homework-failed` when
        // its anti-troll state machine reaches level 9. We catch it on
        // the window, mark the global session state, then jump to the
        // reflection screen (which then advances to results). The
        // sessionLog gets a sentinel item so the backend aggregator
        // can apply the fail flag too — and `_fetchScorecard` reads
        // `window.__homeworkFailed` directly, so the POST body carries
        // the flag even if the sentinel is dropped.
        window.addEventListener('nets:homework-failed', function (ev) {
            if (window.__homeworkFailed) return;  // idempotent
            const detail = (ev && ev.detail) || {};
            const deduction = Number(detail.deduction_pct) || 15;
            window.__homeworkFailed = true;
            window.__warningDeductions = deduction;
            // Best-effort sentinel in the session log so the backend
            // can audit the failure path even if the global is lost
            // (e.g., page reload between tutor event and aggregate POST).
            try {
                if (window.__sessionLog) {
                    window.__sessionLog.push({
                        kind: 'tutor_fail',
                        reason: detail.reason || 'troll-strikes',
                        deduction_pct: deduction,
                        ts: Date.now(),
                    });
                }
            } catch (_) { /* swallow */ }
            // Jump to reflection. The fail overlay in the tutor sticks
            // for 2s before this fires (see showFailOverlay setTimeout),
            // so the student sees the overlay → reflection transition.
            try {
                if (typeof showReflectionScreen === 'function'
                    && typeof reflectionHasContent === 'function'
                    && reflectionHasContent()) {
                    showReflectionScreen(function () {
                        if (typeof showResultsScreen === 'function') {
                            showResultsScreen();
                        }
                    });
                } else if (typeof showResultsScreen === 'function') {
                    // No reflection content — go straight to results.
                    showResultsScreen();
                }
            } catch (e) { /* runtime not ready — page may be loading */ }
        });

        async function showResultsScreen() {
            // Activate the screen immediately so the student doesn't see a
            // blank stretch while we wait for the backend.
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            const sr = document.getElementById('screen-results');
            if (sr) sr.classList.add('active');
            setStage(8);
            // Results phase = 100%. Mark every phase complete in case some
            // earlier phase was bypassed (e.g. fixture had no Reading content
            // and the runtime auto-skipped that interstitial without crossing
            // its action). The bar now reads as fully done.
            completeAllPhases();

            // Fetch the canonical scorecard from /api/grading/aggregate.
            const log = window.__sessionLog || [];
            const card = await _fetchScorecard(log);

            const itemScore = Number(card.overall_pct) || 0;
            const perfHex   = card.perf_class === 'perf-good' ? '#22c55e'
                            : card.perf_class === 'perf-mid'  ? '#eab308'
                            :                                   '#ef4444';

            // Band pill — colour driven entirely by backend's perf_class.
            const bandEl = document.getElementById('results-band');
            if (bandEl) {
                bandEl.textContent = (card.band && card.band.name) || 'Novice';
                bandEl.className = 'screen-results-band ' + card.perf_class;
            }

            // Hero — donut gauge with the backend-calculated score.
            const headline = document.getElementById('results-headline');
            if (headline) {
                const C = 2 * Math.PI * 42;
                const dashOffset = C * (1 - itemScore / 100);
                headline.innerHTML = `
                <div class="screen-results-hero">
                  <div class="results-gauge" role="img" aria-label="Umumiy ball ${itemScore} foiz">
                    <svg viewBox="0 0 100 100" aria-hidden="true">
                      <circle cx="50" cy="50" r="42" class="results-gauge-track" fill="none" stroke-width="9"/>
                      <circle cx="50" cy="50" r="42" class="results-gauge-fill"  fill="none" stroke-width="9"
                              stroke="${perfHex}"
                              stroke-dasharray="${C.toFixed(2)}"
                              stroke-dashoffset="${dashOffset.toFixed(2)}"/>
                    </svg>
                    <div class="results-gauge-center">
                      <div class="results-gauge-pct" style="color:${perfHex}">${itemScore}%</div>
                      <div class="results-gauge-frac">${(card.totals && card.totals.correct) || 0} / ${(card.totals && card.totals.items) || 0} to'g'ri</div>
                    </div>
                  </div>
                </div>`;
            }

            // Per-phase progress bars — built from card.phases.
            const phasesEl = document.getElementById('results-phases');
            if (phasesEl) {
                const phases = card.phases || [];
                const rows = phases.map(p => {
                    const axisLine = (typeof p.axis_1_mean === 'number' && typeof p.axis_2_mean === 'number')
                        ? `<small>A1 ${p.axis_1_mean.toFixed(1)} · A2 ${p.axis_2_mean.toFixed(1)}</small>`
                        : '';
                    return `<div class="results-phase-row">
                      <div class="results-phase-name">${p.label}${axisLine}</div>
                      <div class="results-phase-bar-track">
                        <div class="results-phase-bar-fill ${p.perf_class}" style="width:${p.pct}%"></div>
                      </div>
                      <div class="results-phase-score ${p.perf_class}">${p.score_text}</div>
                    </div>`;
                }).join('');
                phasesEl.innerHTML =
                    `<div class="results-section-title">Faza ko'rsatkichlari</div>
                     <div class="results-phase-list">${rows}</div>`;
            }

            // 2-axis rubric — backend pre-computes mean / perf_class / tag and
            // tells us which rubric applies via card.rubric ("amr" | "lmr").
            // Math/science/social → AMR (Concept Identification + Process Integrity).
            // Language subjects (english/ona-tili/rus-tili) → LMR v2
            // (Grammatical Accuracy + Lexical Quality).
            const amrEl = document.getElementById('results-amr');
            if (amrEl) {
                const isLMR     = (card.rubric === 'lmr');
                const titleKey  = isLMR ? 'res.lmr_title'  : 'res.amr_title';
                const axis1Key  = isLMR ? 'res.lmr_axis1'  : 'res.amr_axis1';
                const axis2Key  = isLMR ? 'res.lmr_axis2'  : 'res.amr_axis2';
                if (card.has_axes) {
                    amrEl.innerHTML = `
                    <div class="results-section-title">${RT(titleKey)}</div>
                    <div class="results-amr-grid">
                      ${_renderAxisBar(RT(axis1Key), card.axes && card.axes.axis_1)}
                      ${_renderAxisBar(RT(axis2Key), card.axes && card.axes.axis_2)}
                    </div>
                    <div class="results-amr-note">
                      ${isLMR
                        ? `2-eksa baholash <strong>faqat ochiq javoblar</strong> uchun
                           qo'llaniladi. Yopiq formatdagi javoblar (variant tanlash,
                           aniq moslik) faza ballariga ta'sir qiladi, lekin eksa
                           o'rtachasiga qo'shilmaydi — chunki rubrika grammatika va
                           so'z tanlashni baholaydi, faqat bitta so'zli javobni emas.`
                        : `2-eksa baholash <strong>faqat 4-faza Real-Life va 6-faza Final Boss</strong>
                           ochiq javoblariga qo'llaniladi. Yopiq formatdagi raqamli javoblar
                           (masalan, "40°") va Sentence Fill javoblari to'g'ri/noto'g'ri
                           sifatida hisoblanadi va faza ballariga ta'sir qiladi, lekin
                           eksa o'rtachasiga qo'shilmaydi — chunki rubrika qoidani nomlash
                           va bosqichma-bosqich asoslashni baholaydi, faqat son javobini emas.`}
                    </div>`;
                } else {
                    amrEl.innerHTML = `
                    <div class="results-section-title">${RT(titleKey)}</div>
                    <div class="results-amr-empty">
                      ${isLMR
                        ? `Bu sessiyada hech qaysi ochiq javob 2-eksa rubrika bo'yicha
                           baholanmadi. LMR to'liq jumlali javoblarni talab qiladi:
                           grammatik to'g'ri va lug'aviy aniq jumla yozing.
                           Faqat bitta so'z yoki kalit so'z javobi rubrikaning
                           past chegarasi (25%) hisoblanadi.`
                        : `Bu sessiyada hech qaysi 4- yoki 6-faza javobi 2-eksa rubrika
                           bo'yicha baholanmadi. AMR ochiq, asoslangan javoblarni talab
                           qiladi: qoidani aniq nomlang ("Pifagor teoremasi"), uni masala
                           shartiga bog'lang, va bosqichma-bosqich yeching. Faqat son
                           javobi rubrikaning past chegarasi (25%) hisoblanadi.`}
                    </div>`;
                }
            }

            // Coaching tip — text from backend, perf class for the tint.
            const masteryEl = document.getElementById('results-mastery');
            if (masteryEl) {
                masteryEl.textContent = card.coaching_tip || '';
                masteryEl.className = 'screen-results-mastery ' + card.perf_class;
            }

            const closingEl = document.getElementById('results-closing');
            if (closingEl) {
                closingEl.textContent = RT('res.closing');
            }

            // Footer action — kind + label + class come from backend.
            // Per GRADING.md: >= 60% renders Tugatish (finish), < 60% Qayta bajarish (restart).
            const actionsEl = document.getElementById('results-actions');
            if (actionsEl && card.action) {
                actionsEl.innerHTML = '';
                const b = document.createElement('button');
                b.className   = 'results-action-btn ' + card.action.perf_class;
                b.textContent = card.action.label;
                b.addEventListener('click', () => {
                    if (card.action.kind === 'finish') {
                        try { window.location.href = '/'; } catch (_) {}
                    } else {
                        try { window.location.reload(); } catch (_) {}
                    }
                });
                actionsEl.appendChild(b);
            }

            // Final button — reset to "done" state.
            btn.classList.remove('pulse', 'state-pill');
            btn.classList.add('state-line');
            if (btnText) btnText.style.opacity = '0';
            // Expose the backend's payload for tests / future export.
            window.__sessionAggregate = card;
        }
