# -*- coding: utf-8 -*-
"""Texts for volume 01 ("O jogo em resumo", "Classes e sistemas") and volume 05 ("Outras fontes", press tables),
merged in on 2026-09-24 from Diego's "Saint Seiya Online - Notas de Pesquisa" and "Surplices" documents and from
the Baidu Baike entry of the game. Everything is a summary in my own words (no copied text); skill, system and
dungeon names are the official pt-BR names found in the client's LANG data (element/data/lang_pt-BR.data).
Image paths are relative to the dump folder."""

GAME_FACTS = [
    ("Nome", "Saint Seiya Online (圣斗士星矢Online)"),
    ("Gênero", "MMORPG 3D para PC"),
    ("Desenvolvimento", "Perfect World (完美世界, antiga 完美时空), com o motor próprio Athena 3D"),
    ("Licença e supervisão", "obra de Masami Kurumada, que supervisionou o jogo; a Baidu Baike credita a licença à SEGA, outras fontes à Shueisha"),
    ("Fontes da história", "o mangá original e dois romances licenciados, Capítulo de Sangue (血之章) e Capítulo da Aliança (盟之章), dos quais sai parte do conteúdo original do jogo"),
    ("Lançamento na China", "16 de maio de 2013, depois de testes fechados em 2012 e 2013"),
    ("Última versão chinesa", "Batalha dos Deuses (诸神之战)"),
    ("Encerramento na China", "aviso oficial em outubro de 2018; servidores desligados em 31 de dezembro de 2018"),
    ("Lançamento no Brasil e na América Latina", "setembro de 2017, pela Ongame (parceria SEGA e Perfect World), em português e espanhol; primeira versão fora da China"),
    ("Encerramento no Brasil", "loja fechada em 30 de abril de 2020; servidores desligados até o fim de junho de 2020"),
    ("Hoje", "servidor de fãs Seiya Reborn, de onde vêm os arquivos deste livro"),
]

LAUNCH_BR = [
    "A versão brasileira, distribuída pela Ongame, era a build chinesa mais recente da época, chamada Movimento de Deus (é o nome do vídeo da tela de login). O beta fechado foi de 29 de agosto a 3 de setembro de 2017, com inscrições de 23 a 28 de agosto; o beta aberto veio logo depois, em setembro, em português e espanhol.",
    "A localização foi feita em legendas. Só os dois personagens originais que guiam o herói, um masculino e um feminino, ganharam vozes em português, de Arthur Machado e Kandy Kathy; a dublagem completa chegou a ser cogitada, mas nunca saiu. A loja do jogo fechou em 30 de abril de 2020 e os servidores foram desligados até o fim de junho de 2020, cerca de um ano e meio depois do fim da versão chinesa.",
]

SETTING = [
    "Segundo a Baidu Baike, o ponto de partida do jogo é o fim da Guerra Santa anterior, da qual só Shion e Dohko sobreviveram. Sabendo que 88 Cavaleiros não bastariam para as guerras que viriam, Shion passou a reunir jovens aspirantes e a treiná-los; quem passava no treino mas não recebia uma Armadura continuava no Santuário, formando um exército a serviço de Athena.",
    "Quando Saga toma o lugar do Grande Mestre, ele herda esse exército e o plano de recrutamento, e tenta transformá-lo em tropa pessoal. Ao mesmo tempo se aproximam as guerras contra Poseidon e Hades, o despertar dos Gigantes e os conflitos entre os deuses gregos, enquanto dentro do Santuário cresce uma conspiração que envolve Cavaleiros de Bronze, Prata e Ouro. O herói do jogo é um desses aspirantes: sem Armadura no começo, entra como guarda do Santuário e luta ao lado dos Cavaleiros em cada Guerra Santa.",
]

ARCS = [
    "Uma prévia do beta de 2013 (UPC Games) descreve o jogo percorrendo os arcos clássicos, com conteúdo original entre eles: a Guerra Galáctica e o recrutamento dos Cavaleiros de Bronze (com os Cavaleiros Negros e os de Prata), o Santuário e as Doze Casas, a Saga de Poseidon e a Saga de Hades.",
    "A Saga de Hades cresceu ao longo de várias atualizações chinesas: a expansão Retorno dos Mortos (亡者归来) trouxe uma raide das Doze Casas de Ouro, e um arco posterior dos Campos Elísios (极乐净土) fechou a história de Hades, com o herói enfrentando o verdadeiro corpo de Hades para libertar Athena, uma grande zona de batalha entre as três facções e um chefe mundial voador recorrente.",
    "Há também uma vertente nórdica, com Valquíria no papel da representante de Odin na Terra e Loki entre os deuses, e figuras olímpicas como Ares e Afrodite, que o próprio catálogo de personagens do jogo coloca entre os deuses. Nas cinemáticas, Ares aparece como uma ameaça do mesmo porte de Hades e Poseidon.",
]
ARCS_IMAGE = ("web/notas/hipermito-ares-hades-poseidon.png",
              "Cinemática do jogo: uma figura nas sombras entre a lança de Ares e o tridente de Poseidon, com as asas de Hades ao centro; a legenda diz que Athena guia a juventude da esperança (captura de Diego)")

CLASSES_INTRO = ("O herói escolhe uma das cinco constelações de Bronze clássicas; mais tarde o jogo acrescentou o Dragão Marinho, "
                 "para os aspirantes de Poseidon, e o Wyrm (Estrela Celeste do Prestígio), para os de Hades. O quadro abaixo resume "
                 "a descrição da Baidu Baike e a prévia do beta (UPC Games); os nomes das técnicas são os da versão brasileira.")

CLASSES = [
    {"name": "Pégaso", "zh": "天马座", "range": "corpo a corpo", "role": "dano explosivo e contínuo (DPS equilibrado, boa defesa)",
     "text": "Acumula pontos de energia a cada golpe seguido no mesmo alvo e os gasta em finalizações mais fortes; é o mais móvel das classes, com aceleração que também livra de lentidão e imobilização, arremessa o alvo ao chão e reforça o dano de todo o grupo.",
     "skills": [("Meteoro de Pégasus", "天马流星拳", "avança de longe e derruba o alvo e quem estiver perto"), ("Punho de Meteoro", "流星空突拳", "golpe básico rápido"),
                ("Golpe giratório de Pégaso (tradução minha; sem nome na versão brasileira)", "天马回旋击碎拳", "finalização: gasta toda a energia, levanta o alvo e o arremessa"),
                ("Asas de Pégasus", "天马之翼", "mais velocidade e esquiva por alguns segundos, imune a imobilização e lentidão"),
                ("Expl. de Meteoro", "流星爆裂拳", "finalização básica que gasta toda a energia"), ("Força da União", "星魂降临", "aumenta o dano de todo o grupo por um tempo")]},
    {"name": "Dragão", "zh": "天龙座", "range": "corpo a corpo", "role": "tanque",
     "text": "Treinado em Rozan e protegido pelo escudo da Armadura, tem a maior vida e defesa: atrai a atenção dos inimigos para si, recebe mais cura quando tratado por Andrômeda, controla grupos e protege os companheiros.",
     "skills": [("Cólera do Dragão", "庐山升龙霸", "o golpe que inverte a cachoeira de Rozan, lança o alvo longe"), ("Sacrif. do Dragão", "真龙连牙", "ataques furiosos pagos com a própria vida"),
                ("Dragão Nascente", "升龙霸", "versão básica da Cólera do Dragão"), ("Dragão Voador", "庐山龙飞翔", "vira um dragão, atravessa o alvo e para atrás dele"),
                ("Escudo do Dragão", "龙纹之盾", "escudo que anula o dano recebido"), ("Círculo do Dragão", "升龙阵", "protege a si e aos aliados em volta")]},
    {"name": "Cisne", "zh": "白鸟座", "range": "à distância", "role": "mago de controle e dano em área",
     "text": "Formado na Sibéria, ataca de longe com o ar congelante: deixa os inimigos lentos ou congelados, arma bombas de gelo no chão, tem ataques em área, enfraquece a defesa do alvo e livra os aliados de efeitos de controle. Precisa refinar a Armadura para atacar mais rápido.",
     "skills": [("Pó de Diamante", "钻石星辰拳", "golpe avançado de frio polar"), ("Dança do Cisne", "白鸟之舞", "solta frio em volta, deixa os inimigos lentos e salta para trás"),
                ("Caixão Gélido", "冰柩", "congela o alvo"), ("Terra Gélida", "冰封大地", "área gelada que acaba congelando quem fica nela"),
                ("Punho de Diamante", "钻石巨拳", "golpe básico à distância"), ("Explosão Aurora", "曙光女神的宽恕", "golpe supremo, atinge também quem está no caminho")]},
    {"name": "Andrômeda", "zh": "仙女座", "range": "média distância", "role": "curandeiro e dano (híbrido)",
     "text": "A única classe de Bronze que cura: alterna entre curar e causar dano, cura com bônus o Dragão, junta os inimigos espalhados para o Cisne e o Pégaso e livra os aliados de controle. É a classe mais versátil, mas a mais exigente.",
     "skills": [("Corrente de Andrômeda", "星云锁链", "empurra os inimigos e arma um labirinto de correntes que os deixa lentos"), ("Tempestade Nebulosa", "星云风暴", "enrola o alvo e o bate no chão, atingindo quem está perto"),
                ("Benção da Corrente", "锁链加持", "transmite força a um aliado, que causa muito mais dano"), ("Barre. de Luz Est.", "星光壁障", "reduz ao mínimo o dano direto que o aliado recebe"),
                ("Luz Est. da Liberd.", "自由星光", "livra o aliado de controle e o protege por um tempo"), ("Corrente do Dest.", "命运圆锁", "paralisa o alvo e puxa os monstros em volta para junto dele")]},
    {"name": "Fênix", "zh": "凤凰座", "range": "à distância", "role": "dano contínuo e controle de um alvo; invoca Cavaleiros Negros",
     "text": "Saída da Ilha da Rainha da Morte, queima os alvos com dano que se acumula, tem o melhor controle sobre um único inimigo e o maior dano em área puro entre os Bronze (sem gelo nem controle), invoca Cavaleiros Negros e renasce; tem pouca defesa, compensada por fugas em voo.",
     "skills": [("Ave Fênix", "凤翼天翔", "invoca a fênix de fogo sobre uma área e deixa os alvos inflamáveis e em chamas"), ("Golpe Fantasma da Fênix", "凤凰幻魔拳", "ataque mental que confunde; quanto mais queimaduras, mais dano"),
                ("Aparição de Fênix", "凤凰现临", "golpe forte que respinga nos vizinhos e piora as queimaduras"), ("Golpe das Sombras", "死亡皇后之焰", "uma imagem de Fênix avança e prende os pés dos inimigos"),
                ("Chamas da Fúria", "怒火之焰", "atinge o alvo e os vizinhos e os põe em chamas"), ("Matança e Ódio", "憎恨虐杀", "puxa o alvo, golpeia e o lança longe")]},
    {"name": "Dragão Marinho", "zh": "海龙座", "range": "à distância", "role": "dupla personalidade: cura e controle, ou dano à distância",
     "text": "Classe de Poseidon com uma balança interior: no lado do bem cura e controla, com dano médio; no lado do mal causa muito dano à distância e controla grupos. As técnicas usadas movem a balança, e cada lado fortalece as técnicas do seu tipo; cria ilusões múltiplas.",
     "skills": [("Triângulo de Ouro", "黄金三角次元", "técnica exclusiva da Escama de Dragão Marinho")]},
    {"name": "Wyrm (Estrela Celeste do Prestígio)", "zh": "天威星", "range": "corpo a corpo", "role": "dano explosivo que também defende",
     "text": "Classe de Hades: transforma-se em dragão demoníaco, absorve dano e muda de posição. Segundo a Baidu Baike, a Estrela Celeste do Prestígio seria a forma renascida da Estrela Celeste Feroz (Radamanthys de Wyvern): depois de cair no Santuário junto com Kanon, ele teria sido salvo por Pandora. A galeria de Cerberus-rack (volume 05) sustenta o contrário, que a Sapuris de Wyrm é outra, e não uma versão da de Wyvern.",
     "skills": [("Onda de Choque", "翼龙冲击波", "técnica exclusiva da Sapuris")]},
]
CLASSES_PROGRESSION = ("O herói passa das Armaduras de Bronze para as variantes secundárias de Bronze e depois para Prata (em geral a partir do nível 60) "
                       "e Ouro, por nível e refinamento. A versão brasileira acabou com 23 classes de Sapuris para os aspirantes de Hades, "
                       "listadas com as correções de Diego no volume 03.")
CLASSES_IMAGE = ("web/notas/selecao-das-23-classes-de-sapuris.png", "Tela de seleção das 23 classes de Sapuris (captura de Diego)")

SYSTEMS = [
    ("Armadura", "圣衣", "Dá atributos enquanto vestida e uma bênção permanente da constelação, traz técnicas próprias e encaixes de Habilidade de Armadura (斗魂) que reforçam as técnicas do herói. Com treino, algumas Armaduras evoluem até formas que superam as de Ouro e as Divinas. Refinar (星铸) fortalece tudo isso de uma vez."),
    ("Relíquia", "神器", "Sobe por cinco estágios, Bronze, Prata, Ouro, Divino e Perfeito, conforme o poder divino acumulado; coleções completas de Relíquias ativam bônus extras."),
    ("Equipamento", "防具", "Faixa, camisa, calça, anel, colar e amuleto têm atributos em parte aleatórios; pedra espiritual, emblema e bracelete têm atributos fixos e sobem de grau com materiais. A qualidade vai do branco ao laranja, com o dourado lendário acima. Aprimorar (聚能) sorteia valores dentro de uma faixa e só guarda o melhor; o resultado pode ser transferido para outra peça, e runas dão bônus temporários."),
    ("Caixa Mágica", "魔盒", "Gasta uma energia que se recupera com o tempo de jogo; desmonta equipamentos em materiais e sobe o grau de pedra, emblema e bracelete sem risco de falha."),
    ("Alma", "星魂", "Obtida em dungeons e com o potencial do Cosmo, em quatro qualidades (verde, azul, roxa e laranja); uma Alma alimenta outra de qualidade igual ou maior."),
    ("Reputação", "声望", "Três tipos: por região (amigável, respeitado, reverenciado), com Cavaleiros de Ouro e Prata (amigável, próximo, confidente) e a de campo de batalha, ganha nas Ruínas de Ática e trocada por prêmios."),
    ("Conquistas", "成就", "Registradas nos anais do Santuário, em categorias de crescimento pessoal, missões, dungeons, vida social, exploração e desafios épicos."),
    ("Álbum", "图鉴", "Personagens, Armaduras e cenários. Na primeira versão tinha 38 personagens (13 de Ouro, 3 de Prata, 11 de Bronze, 2 Marinas, 5 Cavaleiros Negros e 4 outros), ganhos com as missões do Professor Kurumada, e 61 Armaduras (20 de Bronze, 20 de Prata, 12 de Ouro, 8 Sapuris e 1 Escama). Biografias e livros de geografia achados pelo mundo completam cada ficha com bônus permanentes. A versão final tem 165 cartões (volumes 02 e 03)."),
    ("Títulos", "称号", "Aparecem sobre o nome e dão bônus: só um título de habilidade fica ativo por vez, e alguns dão bônus permanentes. Vêm da história, da reputação, de encontros raros, da vida social, dos rankings e das conquistas do exército."),
    ("Cosmo", "小宇宙", "Liberado no nível 45; reforça os atributos e o ganho de cada explosão de Cosmo, que fica mais forte quanto mais energia foi acumulada na luta. Tem duas telas, a do Cosmo e a das Almas."),
]
DUNGEONS = [
    ("Atlântida", "亚特兰蒂斯", "3 a 6 jogadores, níveis 25 a 100, o dia todo", "O navio é atacado; depois de vencer os monstros e o Cavalo-Marinho de Escama, o grupo desce ao oceano e enfrenta Moses de Baleia Negra, o Kraken e Io de Scylla antes do Dragão Marinho no seu altar."),
    ("Crise das Doze Casas", "十二宫危机", "3 a 6 jogadores, níveis 20 a 100, das 12h às 14h e das 20h às 22h", "Aberta pelo capitão da guarda na área de comércio do Santuário; uma vez por dia, com monstros no nível médio do grupo."),
    ("Proteja Athena", "女神近卫军", "3 a 6 jogadores (ou 3 a 12 no modo de herança), níveis 25 a 100, em quatro horários", "Tem um modo normal e um avançado em que jogadores de nível alto recebem pontos por ajudar os de nível baixo."),
    ("Memórias da Guerra Santa", "圣战回忆", "3 a 6 jogadores, a partir do nível 18, duas vezes por dia", "Dohko pede que o grupo derrote o Espectro da Estrela Celeste da Derrota (Troll)."),
    ("Dez Cavernas", "十风穴", "2 a 6 jogadores, a partir do nível 35, dez vezes por semana", "Kiki guia o grupo por saltos duplos e túneis de pedras que caem, passando pelos Cavaleiros Negros de Pégaso, Cisne, Andrômeda e Dragão até Ikki de Fênix."),
]
REQUIREMENTS = [["", "Mínimo", "Recomendado"],
                ["Processador", "2,4 GHz", "3,2 GHz"],
                ["Memória", "1 GB", "4 GB"],
                ["Disco", "8 GB livres", "8 GB livres"],
                ["Placa de vídeo", "GeForce 9500 GT / Radeon HD 3850", "GeForce 8800 GTX / Radeon HD 4850"],
                ["Memória de vídeo", "256 MB", "1 GB"],
                ["Internet", "ADSL ou linha dedicada", "ADSL ou linha dedicada"]]
REVIEWS = [
    ("52pk", "elogiou o combate rápido, a fidelidade à história original e o visual próprio; criticou a sensação de impacto dos golpes e os efeitos sonoros."),
    ("Sina Games", "destacou as animações ligadas às missões, que fazem o jogador viver a história no papel de vários personagens em vez de só assistir."),
]

OTHER_SOURCES = [
    ("Baidu Baike: 圣斗士星矢Online", "https://baike.baidu.com/item/%E5%9C%A3%E6%96%97%E5%A3%AB%E6%98%9F%E7%9F%A2Online/10994393",
     "Enciclopédia chinesa: ficha do jogo (lançamento em 16/05/2013, motor Athena 3D, fim em 31/12/2018), a ambientação, as sete classes com técnicas, os sistemas, mapas, requisitos, cinco dungeons e duas análises. Resumida no volume 01, em \"O jogo em resumo\" e \"Classes e sistemas\"."),
    ("Wikipédia em chinês: 圣斗士星矢Online", "https://zh.wikipedia.org/wiki/%E5%9C%A3%E6%96%97%E5%A3%AB%E6%98%9F%E7%9F%A2Online",
     "Visão geral: desenvolvimento pela Perfect World, fontes da história (mangá e os romances Capítulo de Sangue e Capítulo da Aliança) e as datas de lançamento e encerramento."),
    ("Perfect World: aviso de encerramento", "http://seiya.wanmei.com/news/gamebroad/20181026/214965.shtml",
     "O comunicado oficial de outubro de 2018 que anunciou o fim da versão chinesa."),
    ("TGBUS: anúncio de novo servidor", "https://m.tgbus.com/news/95185", "Notícia chinesa sobre a abertura de um novo servidor do jogo."),
    ("UPC Games: O que você precisa saber sobre S.S.O", "https://canalupcgames.blogspot.com/2013/08/oque-voce-precisa-saber-sobre-sso.html",
     "Prévia brasileira do beta chinês de 2013: os arcos da história, as cinco classes com o papel de cada uma e a progressão de Bronze a Prata e Ouro."),
    ("Diego Maryo: Saint Seiya Online no Brasil", "https://diegomaryo.cdz.com.br/saint-seiya-online-no-brasil/",
     "O lançamento brasileiro: build Movimento de Deus, datas do beta, legendas e os dois personagens dublados por Arthur Machado e Kandy Kathy."),
    ("Anime United: MMORPG será descontinuado no Brasil", "https://www.animeunited.com.br/noticias/games/saint-seiya-online-mm/",
     "O fim da versão brasileira: loja fechada em 30 de abril de 2020 e servidores desligados até o fim de junho de 2020."),
]

# CavZodiaco articles about the cloths: which earlier work each cloth came from (per the articles, as collected in the notes)
PRESS_TABLES = {
    "2018-02-16": [["Armadura (Bronze)", "Onde apareceu antes", "Destaque"],
                   ["Escudo", "Yan de Escudo (filme da deusa Éris) / Juan de Escudo (Saintia Shō)", "grande escudo de defesa e contra-ataque no braço esquerdo"],
                   ["Sextante", "Yuuri (Gigantomachia)", "Armadura de instrumento astronômico; a Astromancia ressoa com as outras Armaduras"],
                   ["Peixe Voador (Volans)", "Argo (Ômega) / Cavaleiro sem nome (Lost Canvas)", "força do mar, ataques em redemoinho"],
                   ["Serpente", "exclusiva do jogo", "venenos, remédios e luta"],
                   ["Peixe Austral", "exclusiva do jogo", "forças místicas do oceano; técnica Águas Escarlate"],
                   ["Camaleão", "June (série clássica)", "ataques com o chicote"],
                   ["Hidra Macho", "Ichi (Ômega)", "presas venenosas retráteis; diferente da Hidra Fêmea"],
                   ["Coroa Boreal", "Dali (Ômega) / Katya (Saintia Shō)", "força de vontade; sente o perigo à distância"],
                   ["Coroa Austral", "exclusiva do jogo", "origem mantida em mistério"],
                   ["Cruzeiro do Sul", "Kraisto (Christ) (filme da deusa Éris) / Kazuma (Ômega) / George (Saintia Shō)", "a menor constelação; poucos são dignos de vesti-la"],
                   ["Popa", "Lacaille (Lost Canvas)", "parte do trio do navio Argo, com Quilha e Velas"],
                   ["Rena", "Rudolph (Ômega)", "constelação extinta; empresta elementos da Girafa"],
                   ["Erídano", "Cavaleiro sem nome (Lost Canvas)", "rio divino da mitologia; técnica Força Fluente"],
                   ["Oriolus de Prata", "exclusiva do jogo", "uma das poucas Armaduras que não vêm de constelação; ave asiática"]],
    "2018-03-02": [["Armadura (Prata)", "Onde apareceu antes", "Técnica em destaque"],
                   ["Bússola (Pyxis)", "Rusk (Bronze no Lost Canvas)", "Curso da Morte: cosmo disparado em linha reta"],
                   ["Baleia", "Mouses (Lost Canvas) / Menkar (Ômega)", "Impacto das Profundezas: baleias de água explosivas"],
                   ["Perseu", "Algol", "Olhar de Medusa, a petrificação do escudo"],
                   ["Cassiopeia", "Elda (Saintia Shō)", "nome da rainha vaidosa do mito"],
                   ["Pavão", "Shiva (discípulo de Shaka) / Mayura (Saintia Shō) / Pavlin (Ômega)", "Golpe dos Mil Braços: cinco golpes rápidos"],
                   ["Atrium", "exclusiva do jogo", "Cair da Noite escurece a área e enfraquece os inimigos"],
                   ["Flecha (Sagitta)", "Ptolomeu (Tremy no anime)", "Flechas Fantasma confundem o oponente"],
                   ["Cães de Caça", "Asterion / Renner / Miguel (Ômega)", "Punhos Fantasma: muitos golpes rápidos"],
                   ["Lagarto", "Misty", "Barreira de Ar: vento criado pelo movimento rápido"],
                   ["Taça", "Suikyō (Next Dimension) / Aison (Saintia Shō)", "uma das três Armaduras perdidas; vê o futuro e cura com a água"],
                   ["Cérbero", "Dante / Dorer (Ômega)", "Maça Infernal: imobiliza e lança uma bola de fogo"],
                   ["Grou", "Yuzuhira (Lost Canvas) / Komachi (Ômega, Bronze)", "teletransporte com poder psíquico"],
                   ["Altar", "Hakurei (Lost Canvas) / Nikol (Gigantomachia)", "Absorção de Espírito drena a energia do inimigo"],
                   ["Mestre dos Fantasmas", "Jisty (exclusivo do anime)", "invoca espíritos vingativos"],
                   ["Serpentário (Ofiúco)", "Shina (Lost Canvas) / Odysseus (Next Dimension, Ouro)", "Garras do Trovão atordoam o alvo"],
                   ["Mensa", "exclusiva do jogo", "Fúria do Titã aumenta o poder de combate"]],
}

# richer versions of existing press / DeviantArt summaries (replace the short ones in story_config)
PRESS_NOTES_EXTRA = {
    "2018-02-09": "Os personagens exclusivos do jogo. Rodório foi o primeiro Cavaleiro de Pégaso: morto numa Guerra Santa anterior, volta com o corpo feito de chamas e uma réplica da Armadura, lembrando pouco da vida passada, para proteger o selo de Athena, e se sacrifica contra Thanatos com uma técnica suicida parecida com a de Shiryu para o herói fugir com o sangue de Hades. Lei-Hu, rival de Shiryu expulso de Rozan pela ambição, volta para uma revanche, luta ao lado dele contra Máscara da Morte, é possuído pelo cosmo do Cavaleiro de Câncer e acaba libertado por Shiryu. Sher-Khan, exilado da Estrada Esquecida, espiona de máscara (para poupar Athena da vergonha) uma conspiração em torno do Grande Mestre e é morto por Saga ao descobrir que Shion foi assassinado. Perséfone guarda a árvore Mokurenji; Lamech, deus do Nada que quer apagar o universo, é o chefe voador do evento Névoa Vermelha; Sillas, seu servo leal, caça os Cavaleiros em combate honrado; Valquíria faz o papel de Hilda como uma guerreira implacável de armadura dourada, chefe do Santuário de Gelo. A matéria cita ainda Aiya, Eide, Alex, Alexer, Natássia, Acer, Taylor, Wyrm e os Espectros originais.",
    "2017-08-22": "A Ongame anuncia o lançamento oficial no Brasil em setembro, com trailer e primeiras impressões; inscrições para o beta fechado de 23 a 28 de agosto, e o beta de 29 de agosto a 3 de setembro de 2017.",
}
DA_NOTES_EXTRA = {
    "710444922": "June renegada: numa missão o herói enfrenta June de Camaleão vestindo uma Sapuris a serviço de Hades; o catálogo do jogo a põe entre os Cavaleiros ressuscitados, o que sugere que ela morreu na história do jogo, embora o artista não tenha achado a missão que explica como.",
    "711329206": "Asceta, o primeiro Marina encontrado no jogo além dos generais, dos soldados e de Thetis; o catálogo o liga à constelação de Dourado (peixe-espada).",
    "883561355": "Perséfone, imperatriz do Submundo, em ficha de personagem feita em 2021 a pedido de Diego, porque só existe no jogo: guarda a árvore Mokurenji e é um dos chefes antes de Hades.",
    "846875136": "Wyrm é a classe de Espectro jogável; a V2 azul representa a Prata, a V3 é a V2 dourada; como Atavaka no Lost Canvas, o Espectro que a veste também se chama Wyrm (sistema Anima). É loiro, usa as técnicas Tornado das Asas Gigantes e Onda de Choque, e a Sapuris não é uma versão da Wyvern de Radamanthys.",
    "843838056": "No jogo não há os soldados-esqueleto do anime: os soldados espectrais poderiam representar as árvores Jubokko do folclore japonês (ideia de BuraianZ).",
    "709474922": "Um Espectro de Bennu, a partir de um desenho de Shiori Teshirogi para o Lost Canvas, contado entre os Espectros do jogo.",
}

# ---------------------------------------------------------------------------------------------------------------
# Appendix volumes 14-17: every player-facing pt-BR string of the client (element/data/lang_pt-BR.data) that the
# other volumes do not already show, by LANG section. (section, title, intro, leftovers_only)
# leftovers_only = the section is mostly in volumes 01-13 already; only strings not found there are listed.
# data_config is left out on purpose: 125k internal labels of effect/config records (developer names in machine
# translation, never shown to the player).
LANG_APPENDIX = [
    ("14", "Apêndice I: itens, equipamentos e tesouros", [
        ("data_item", "Itens: nomes e textos dos registros", "Os nomes de todos os itens do jogo, com o original chinês ao lado dos nomes curtos, e os outros campos dos registros (descrições alternativas, textos da barra de progresso, nomes curtos das Almas).", False),
        ("item", "Itens: descrições, efeitos e mensagens", "Descrições, atributos e mensagens de uso dos itens, na ordem do arquivo do jogo.", False),
        ("data_equip", "Equipamentos", "Nomes e textos dos equipamentos (faixas, camisas, anéis, colares, amuletos, emblemas...).", False),
        ("data_treasures", "Tesouros e baús", "Os tesouros, baús e pacotes de recompensa.", False),
        ("data_recipe", "Receitas", "As receitas de fabricação.", False),
        ("lottery", "Sorteios e roletas", "Os textos dos sorteios, roletas e loterias de eventos.", False),
    ]),
    ("15", "Apêndice J: técnicas", [
        ("skill", "Técnicas: nomes, descrições e efeitos", "Todas as técnicas do herói, das classes, das Armaduras, dos pets e dos monstros, com nomes, descrições, efeitos por nível e mensagens, na ordem do arquivo do jogo.", False),
    ]),
    ("16", "Apêndice K: NPCs, monstros e falas de eventos", [
        ("data_npc", "NPCs: nomes, títulos e textos de interação", "Os nomes dos NPCs (com o original chinês), os títulos que aparecem antes e depois do nome, os textos das barras de progresso ao interagir e as páginas das lojas.", False),
        ("data_monster", "Monstros: nomes e textos", "Os nomes dos monstros e chefes, com o original chinês, e os outros campos dos registros.", False),
        ("policy", "Falas e avisos dos eventos roteirizados", "As falas que NPCs e chefes dizem durante eventos, dungeons e batalhas roteirizadas, e os avisos na tela.", False),
        ("ai", "Avisos do sistema e dos chefes", "Mensagens de sistema e das rotinas de inteligência dos chefes (anúncios de benefícios, fases de batalha).", False),
    ]),
    ("17", "Apêndice L: sistemas, ajuda, interface e demais textos", [
        ("help", "Ajuda e dicas", "Os textos da ajuda do jogo e as dicas.", False),
        ("daily", "Atividades diárias e eventos", "A agenda de atividades: nomes, descrições, horários e regras dos eventos.", False),
        ("achievement", "Conquistas", "Os nomes e as condições das conquistas.", False),
        ("dungeon", "Dungeons: mensagens e objetivos", "Mensagens e contadores das dungeons.", False),
        ("title", "Títulos: textos restantes", "Os textos de títulos que não aparecem no Apêndice C (volume 11).", True),
        ("social", "Social: amigos, grupos, exército e correio", "Os textos dos sistemas sociais.", False),
        ("pet", "Pets", "Os textos do sistema de pets.", False),
        ("question", "Perguntas do quiz", "As perguntas e respostas dos quizzes do jogo.", False),
        ("questionaire", "Questionários", "Os questionários de opinião apresentados aos jogadores.", False),
        ("age", "Avisos de tempo de jogo", "Os avisos do sistema de controle de tempo de jogo e idade.", False),
        ("combat", "Mensagens de combate", "As mensagens exibidas durante as lutas.", False),
        ("arena", "Arena", "Os textos da arena.", False),
        ("countbirds", "Contagem de pássaros", "Os textos do minijogo de contar pássaros.", False),
        ("map", "Mapas: textos restantes", "Nomes de lugares e textos de mapas que não aparecem no volume 01.", True),
        ("photobook", "Álbum: textos restantes", "Textos do Álbum que não aparecem nos volumes 02 e 03.", True),
        ("data_text", "Textos diversos: restantes", "Textos avulsos dos dados do jogo que não aparecem nos outros volumes.", True),
        ("quest", "Missões: textos de interface restantes", "Mensagens do sistema de missões que não aparecem nos outros volumes.", True),
        ("data_quest", "Missões: textos restantes", "Textos dos registros de missões que não aparecem nos volumes da história (em geral, janelas de missões duplicadas ou de teste).", True),
        ("animation", "Cinemáticas: textos restantes", "Textos das cinemáticas que não aparecem no Apêndice B (volume 11).", True),
        ("ui", "Interface", "Os textos da interface: botões, janelas e mensagens.", False),
        ("interface", "Interface: janelas", "Os textos das janelas da interface.", False),
        ("common", "Textos comuns", "Textos comuns usados em várias partes do jogo.", False),
        ("error", "Mensagens de erro", "As mensagens de erro do cliente e do servidor.", False),
        ("login", "Login e servidores", "Os textos da tela de login e da escolha de servidor.", False),
        ("config", "Configurações", "Os textos da janela de configurações.", False),
        ("miscs", "Diversos", "Outros textos do cliente.", False),
    ]),
]
LANG_FIELD_LABELS = {"name": "Nomes", "物品名字": "Nomes (segunda lista)", "备选图案文字描述#": "Descrições alternativas",
                     "进度条显示文字": "Texto da barra de progresso", "星魂简称": "Nomes curtos das Almas", "NPC职业前缀": "Títulos antes do nome",
                     "NPC职业后缀": "Títulos depois do nome", "分页#标题": "Títulos das páginas da loja", "第#页名称": "Nomes das páginas da loja",
                     "变身后名称": "Nome depois da transformação", "script": "Mensagens dos scripts", "": "Textos"}
