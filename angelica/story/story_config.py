# -*- coding: utf-8 -*-
"""Estrutura narrativa do documento 'Saint Seiya Online - Story'.
Cada seção lista faixas de IDs de quest (inclusive) na ordem em que devem aparecer, mais uma introdução escrita à mão."""

CHAPTERS = [
 ("Saga do Santuário", "I", "Lendas de uma Nova Era!"), ("Saga do Santuário", "II", "Cavaleiros do Amor e da Justiça!"),
 ("Saga do Santuário", "III", "Guerreiro sob a Via Láctea"), ("Saga do Santuário", "IV", "Os Cavaleiros da Deusa!"),
 ("Saga do Santuário", "V", "Homem que Conhece a Verdade!"), ("Saga do Santuário", "VI", "Fé Milenar Intacta!"),
 ("Saga do Santuário", "VII", "O Cavaleiro de Ouro de Sagitário!"), ("Saga do Santuário", "VIII", "O Domínio Sangrento dos Sete Mares!"),
 ("Saga do Santuário", "IX", "A Ambição de Dominar o Mundo!"), ("Saga do Santuário", "X", "As Chamas da Ilha da Rainha da Morte!"),
 ("Saga do Santuário", "Final", "As Doze Casas de Ouro"),
 ("Saga de Poseidon", "I", "O Poder de Poseidon!"), ("Saga de Poseidon", "II", "A Glória do Extremo Norte!"),
 ("Saga de Poseidon", "III", "A Ira de Poseidon!"), ("Saga de Poseidon", "IV", "O Azul da Fortaleza Submarina!"),
 ("Saga de Hades: Cruzada ao Submundo", "I", "Destruidor Dourado!"), ("Saga de Hades: Cruzada ao Submundo", "II", "O Prólogo da Grande Guerra Santa!"),
 ("Saga de Hades: Cruzada ao Submundo", "III", "A Traição dos Cavaleiros de Ouro!"), ("Saga de Hades: Cruzada ao Submundo", "IV", "Portal que leva ao Submundo!"),
 ("Saga de Hades: Inferno", "I", "Raios Solares do Inferno!"), ("Saga de Hades: Inferno", "II", "Cavaleiros de Ouro!"),
 ("Saga de Hades: Inferno", "Elísios", "Final do Capítulo Paraíso! Retorno ao mundo esperançoso!"),
]

# imagens por região: (mapa do mundo, tela de carregamento / cartão do álbum)
REGION_IMAGES = {
 "constelacoes": ["images/surfaces/maps/worldmaps/n1.dds.png", "images/surfaces/background/loading01.jpg.png", "images/surfaces/res/photobook/群星之地.dds.png"],
 "santuario": ["images/surfaces/maps/worldmaps/n2.dds.png", "images/surfaces/background/loading11.jpg.png", "images/surfaces/res/photobook/圣域.dds.png"],
 "coliseu": ["images/surfaces/maps/worldmaps/n4.dds.png", "images/surfaces/background/loading04.jpg.png", "images/surfaces/res/photobook/银河竞技场.dds.png"],
 "rozan": ["images/surfaces/maps/worldmaps/n3.dds.png", "images/surfaces/background/loading03.jpg.png", "images/surfaces/res/photobook/庐山.dds.png"],
 "estrada": ["images/surfaces/maps/worldmaps/n5.dds.png", "images/surfaces/background/loading07.jpg.png", "images/surfaces/res/photobook/遗忘之路.dds.png"],
 "ilha_rainha": ["images/surfaces/maps/worldmaps/n6.dds.png", "images/surfaces/background/loading19.jpg.png", "images/surfaces/res/photobook/死亡皇后岛.dds.png"],
 "siberia": ["images/surfaces/maps/worldmaps/n7.dds.png", "images/surfaces/background/loading16.jpg.png", "images/surfaces/res/photobook/东西伯利亚.dds.png"],
 "atlantida": ["images/surfaces/maps/worldmaps/n8.dds.png", "images/surfaces/background/loading09.jpg.png", "images/surfaces/res/photobook/亚特兰蒂斯.dds.png"],
 "andromeda": ["images/surfaces/maps/worldmaps/n9.dds.png", "images/surfaces/background/loading14.jpg.png", "images/surfaces/res/photobook/仙女岛.dds.png"],
 "hades_castelo": ["images/surfaces/maps/worldmaps/n10.dds.png", "images/surfaces/background/loading17.jpg.png", "images/surfaces/res/photobook/哈迪斯城.dds.png"],
 "submundo": ["images/surfaces/maps/worldmaps/n11.dds.png", "images/surfaces/background/loading13.jpg.png", "images/surfaces/res/photobook/冥界地狱.png.png"],
 "elisios": ["images/surfaces/maps/worldmaps/n12.dds.png", "images/surfaces/background/loading15.jpg.png"],
 "doze_casas": ["images/surfaces/maps/worldmaps/f12_5.dds.png", "images/surfaces/background/loading12.jpg.png"],
}

# Partes e seções. ranges = lista de (lo, hi); 'alt' = versões alternativas/antigas do mesmo trecho (aparecem depois, em corpo menor)
PARTS = [
 {"id": "santuario", "title": "Saga do Santuário", "intro":
  "A primeira grande saga do jogo acompanha o herói (o personagem do jogador) desde a disputa pela sua primeira Armadura, na Terra das Constelações, "
  "até a invasão das Doze Casas. Ao contrário do mangá, o jogador não é Seiya: é um aspirante que treina ao lado dele sob a tutela de Marin, carrega em suas veias um sangue misterioso "
  "ligado ao primeiro Cavaleiro de Pégaso, Rodório, e acaba envolvido na conspiração do Grande Mestre e nas primeiras tentativas do Submundo de despertar a Armadura Divina de Hades. "
  "A saga percorre a Terra das Constelações, o Santuário, o Coliseu Graad (a Guerra Galáctica), Rozan, a Estrada Esquecida e a Ilha da Rainha da Morte.",
  "sections": [
   {"id": "s1", "chapter": 0, "region": "constelacoes", "title": "Terra das Constelações: a disputa pela Armadura",
    "intro": "Tudo começa na Terra das Constelações, o campo de treinamento junto ao Mar Egeu onde Seiya treina com Marin. O herói acorda de um pesadelo, compete com Seiya e Cássios pela Armadura de Pégaso, ajuda Seiya a encontrar o colar que ele preparou para a irmã, assiste à vitória de Seiya e, enquanto Shina persegue o novo Cavaleiro, descobre que o Cemitério dos Cavaleiros e Star Hill estão sendo violados por um gás negro vindo do Submundo. Em Star Hill uma Ilusão de Ouro o arrasta para Outra Dimensão, e é o despertar do seu Cosmo que o traz de volta. Marin o envia então ao Santuário.\n\nO jogo teve três versões desta abertura, uma para cada facção jogável: o aspirante de Athena (a versão principal, abaixo), o aspirante de Poseidon, guiado por uma Sereia e pelo Tridente, e o aspirante de Hades, guiado por Pandora. As três versões seguem o mesmo roteiro com diálogos próprios e estão reproduzidas na sequência.",
    "ranges": [(20060, 20090)], "alt": [("Versão do aspirante de Poseidon (classe Dragão Marinho)", [(20207, 20224)]), ("Versão do aspirante de Hades (classe Wyrm)", [(20501, 20519)]), ("Versão anterior da mesma abertura", [(2974, 3003), (95, 126), (305, 326), (12175, 12201), (13918, 13989)])]},
   {"id": "s2", "chapter": 1, "region": "santuario", "title": "Santuário: o juramento, Rodório e o Martelo de Prometeu",
    "intro": "No Santuário o herói passa pelo teste de Aioria de Leão, jura fidelidade diante do Grande Mestre e recebe sua primeira missão: investigar o desaparecimento de aspirantes no Campo de Treinamento. A pista leva a Orfeu de Lira, à Vila Rodório e a um antigo campo de batalha onde repousa a alma de Rodório, o primeiro Cavaleiro de Pégaso. O Poço dos Mortos foi aberto; o Submundo tenta reviver a vestimenta de Hades com o sangue do deus, e o aspirante Alex, amigo do herói, revela-se um guerreiro do Submundo. Shaka de Virgem aparece, os Cavaleiros de Ouro se reúnem, e é preciso obter o Martelo de Prometeu, a relíquia dos Titãs, para destruir a Armadura Divina de Hades no topo do Cume da Loucura. Ao final, o Grande Mestre envia o herói ao Oriente, ao Coliseu Graad.\n\nEsta parte existe em duas redações: um resumo curto e bem traduzido (a versão final do jogo) e a redação longa original, que a localização brasileira só recebeu em tradução automática. As duas estão aqui.",
    "ranges": [(20673, 20695)], "alt": [("Redação original completa (tradução automática do jogo)", [(3160, 3310), (455, 683), (1803, 2102), (2287, 2296)])]},
   {"id": "s3", "chapter": 2, "region": "coliseu", "title": "Coliseu Graad: a Guerra Galáctica, a Floresta Aokigahara e as Dez Cavernas",
    "intro": "Na Cidade Prata, no Japão, o herói encontra Hyoga de Cisne, também enviado pelo Grande Mestre, e a Fundação Graad de Saori Kido, que exibe a Armadura de Ouro de Sagitário como prêmio da Guerra Galáctica. Jabu de Unicórnio, Mino e o Orfanato Filhos das Estrelas, o sequestro do órfão Tianyi por Cavaleiros Negros, o reencontro com Seiya, Shiryu e Shun: a trama do torneio corre paralela à do mangá, até que Ikki de Fênix e os Cavaleiros Negros roubam a Armadura de Sagitário. A perseguição atravessa a Floresta Aokigahara, onde as ilusões do Deus do Sonho aprisionam Shun e Seiya, e termina na batalha das Dez Cavernas, com a Armadura de Pégaso renascida por Kiki. Depois vêm a caçada dos Cavaleiros de Prata (Misty, Moses, Jamian de Corvo, Algol), Marin pendurada na cruz e a revelação de que Saori é Athena.",
    "ranges": [(20392, 20447), (20603, 20603)], "alt": [("Redação original completa (tradução automática do jogo)", [(127, 242), (327, 441), (443, 447), (4444, 4520), (5438, 5445), (2098, 2098)]), ("Missões diárias de história do Coliseu Graad", [(20789, 20800)])]},
   {"id": "s4", "chapter": 3, "region": "rozan", "title": "Rozan: Lei-Hu, o Dragão e Máscara da Morte",
    "intro": "Em Rozan, nos Cinco Picos Antigos, Shiryu está cego depois da luta contra Algol e Shunrei procura o remédio lendário para seus olhos. O herói conhece Lei-Hu, o discípulo expulso do Mestre Ancião, rival e amigo de Shiryu, e Li-Yun, o curandeiro da Vila do Dragão Oculto. Máscara da Morte de Câncer contamina a água de Bi Longtan com o Sekishiki e ressuscita os mortos para obrigar Dohko a entregar a Armadura de Libra. A trama passa pela Terra Abençoada, a Lágrima de Athena, o sacrifício de Lei-Hu, possuído pelo cosmo maligno de Câncer, e a fuga de Yomotsu Hirasaka, e termina com Dohko revelando parte da verdade sobre os acontecimentos de treze anos atrás.",
    "ranges": [(782, 874), (1035, 1051), (1092, 1092), (4291, 4291)], "alt": [("Rozan, segunda visita: a memória perdida e o sangue misterioso", [(1320, 1371), (1489, 1540), (1604, 1656)])]},
   {"id": "s5", "chapter": 4, "region": "estrada", "title": "Estrada Esquecida: os exilados, as Deusas do Destino e a verdade de treze anos atrás",
    "intro": "A Estrada Esquecida é o caminho onde Aioros de Sagitário morreu ao salvar Athena bebê. O herói chega ao Acampamento dos Exilados, ajuda o servo Darius, a menina Colomba e o rei exilado Augusto, passa pelo Portal do Passado guardado por Jamian de Corvo e pelos testes das três Moiras (Cloto, Láquesis e Átropos) no Templo do Destino. Na Vila Esquecida, oprimida pelo exército do Santuário, reencontra Aioria e o líder da resistência, Pan, até o Penhasco da Pedra Vermelha, onde o espião Sher-Khan e a dungeon 'Treze anos atrás' revelam a verdade: Saga assassinou o Grande Mestre e Aioros foi caçado por Shura. Cobre os capítulos V a VII da Saga do Santuário.",
    "ranges": [(3035, 3153), (2197, 2197), (2226, 2226), (2898, 2915), (4165, 4166), (4220, 4220)], "alt": []},
   {"id": "s6", "chapter": 7, "region": "estrada", "title": "Cabo Súnion: Julian Solo, Sorento e o prisioneiro dos deuses",
    "intro": "Na praia ao norte da Estrada Esquecida, um jovem sem memória e a flauta de Sorento levam o herói à mansão Solo e ao segredo do clã: Julian é a reencarnação de Poseidon. A Sereia (Thetis) conduz ao Cabo Súnion, à prisão de água onde Kanon de Gêmeos foi acorrentado pelo irmão há treze anos, e a 'ilusão de ouro do traidor dos deuses' conta a história da fuga de Aioros. É o capítulo VIII, 'O Domínio Sangrento dos Sete Mares'.",
    "ranges": [(2826, 2897), (2412, 2412)], "alt": []},
   {"id": "s7", "chapter": 9, "region": "ilha_rainha", "title": "Ilha da Rainha da Morte: os Cavaleiros Negros, Jango ressuscitado e a máscara de Guilty",
    "intro": "Por ordem de Mu e da Deusa, o herói parte para a Ilha da Rainha da Morte, o 'inferno na Terra' onde Ikki treinou. A ilha foi tomada pelos Cavaleiros Negros: Jango, morto por Ikki, voltou à vida e obriga os escravos e aspirantes a vestir Armaduras de Ódio. Com Shun, o aspirante Acer, o escravo Taylor, Hidra Negro e o clã de Tawana (os criadores das Armaduras Negras, descendentes de Guilty), é preciso reconstruir a máscara de Guilty para selar a ilha, enquanto Shaka de Virgem chega para matar Ikki por ordem do Grande Mestre. Termina com a erupção do Vulcão Adormecido, a segunda morte de Jango e o aparente sacrifício de Ikki.",
    "ranges": [(3719, 3828), (3896, 3908), (3949, 3950), (4152, 4152)], "alt": []},
   {"id": "s8", "chapter": 10, "region": "doze_casas", "title": "As Doze Casas de Ouro",
    "intro": "A Batalha das Doze Casas é jogada em dungeons de história e em eventos: Athena atingida pela flecha de Sagita, a Muralha de Cristal de Mu, o Grande Chifre de Aldebaran, as ilusões de Gêmeos, o Sekishiki de Câncer, Aioria despertado, a Rendição Divina de Shaka, o esquife de gelo de Camus, a Excalibur de Shura e o Funeral de Rosas de Afrodite. As missões abaixo são as etapas dessas dungeons; os diálogos falados dentro das Doze Casas (com os nomes dos falantes) estão no apêndice 'Diálogos das dungeons'.",
    "ranges": [(79, 94), (7190, 7192), (7350, 7350), (8512, 8512), (8799, 8799), (9104, 9104), (9830, 9830), (9880, 9880), (9996, 9996), (10067, 10067), (10451, 10468), (10539, 10539), (11067, 11067), (11475, 11475), (11277, 11278), (11808, 11808), (6271, 6271)], "alt": []},
  ]},
 {"id": "poseidon", "title": "Saga de Poseidon", "intro":
  "O despertar de Poseidon começa com um tsunami mundial. Athena manda o herói à Sibéria Oriental, terra de Hyoga, onde o Guerreiro do Gelo Azul Alexer e o Marina Isaac de Kraken disputam o Oricalco, e a Valquíria, representante de Odin, recupera o anel dos Nibelungos em Yggdrasil. Depois de Kanon se revelar como o General de Dragão Marinho, Saori é sequestrada e a saga segue para Atlântida: a Vila de Nereus, Thetis, Baian de Cavalo Marinho, o Coração do Golfinho, Crisaor, Isaac contra Hyoga, a Armadura de Libra trazida por Shina e a destruição do Pilar Principal.",
  "sections": [
   {"id": "p1", "chapter": 11, "region": "siberia", "title": "Sibéria Oriental: o Oricalco, Alexer e a Valquíria",
    "intro": "A trama da Sibéria Oriental é inteiramente original do jogo. Ela mistura a saga de Poseidon com a mitologia nórdica: a Vila Kohoutek e a Parede de Gelo Eterno, o naufrágio da mãe de Hyoga, a princesa Natássia e seu irmão Alexer (uma releitura de Alexei dos Guerreiros Azuis), Isaac de Kraken e Kanon, que se apresenta como Cavaleiro de Ouro de Gêmeos, e a Valquíria, que reúne os clãs do Norte e do Gelo Azul para tomar o Castelo do Graad Azul, onde Hyoga usa a Execução Aurora e Kanon se revela o General de Dragão Marinho.",
    "ranges": [(4582, 4679), (5678, 5678), (5724, 5724)], "alt": []},
   {"id": "p2", "chapter": 13, "region": "atlantida", "title": "Atlântida: a Vila de Nereus, os Sete Pilares e o Pilar Principal",
    "intro": "Passando pelo turbilhão, o herói chega ao reino submarino: os náufragos Jafé, Arnold e Raul, a Vila de Nereus (descendentes do antigo Imperador dos Mares), Thetis e seu passado, o General Baian, a Floresta de Coral e as Sirenes, o velho mordomo de Julian, o guarda Shuya (que morre para abrir o Templo de Poseidon), o General de Kraken e suas ilusões, Kiki prisioneiro, o Grande Muro de Bimini, Crisaor e a Lança de Ouro, Isaac contra Hyoga, Skilla, a Armadura de Libra e a queda do Pilar Principal onde Athena estava presa.",
    "ranges": [(4776, 4884), (4552, 4552), (5367, 5368)], "alt": []},
  ]},
 {"id": "hades1", "title": "Saga de Hades: Cruzada ao Submundo", "intro":
  "A Guerra Santa contra Hades começa na Ilha de Andrômeda, onde os Espectros abrem uma fissura para o Submundo, passa pelo Santuário (a morte de Athena, a 'traição' de Saga, Camus e Shura ressuscitados) e chega ao Castelo de Hades, o Castelo Heinstein de Pandora, protegido pelos encantamentos dos deuses gêmeos Thanatos e Hypnos.",
  "sections": [
   {"id": "h1", "chapter": 15, "region": "andromeda", "title": "Ilha de Andrômeda: June, Albiore e o Vulcão do Tártaro",
    "intro": "Athena manda investigar manifestações de cosmo na ilha onde Shun obteve sua Armadura. O faroleiro Harden, a Vila do Golfo, Sorento, a Taça do Vencedor, June de Camaleão (que não acredita na ameaça), o mestre Albiore, as borboletas do Submundo, os Cavaleiros de Prata ressuscitados (Algol de Perseu, Moses) e três Espectros no Vulcão do Tártaro, até selar a fissura com água abençoada e voltar ao Santuário para a Guerra Santa.",
    "ranges": [(5947, 6044)], "alt": []},
   {"id": "h2", "chapter": 16, "region": "santuario", "title": "Santuário: a morte de Athena e os Cavaleiros de Ouro ressuscitados",
    "intro": "Athena está morta; Saga, Camus e Shura, revividos por Hades, atacam as Doze Casas. Na Floresta do Crepúsculo, Zeros de Sapo e os Cavaleiros de Ouro em lágrimas explicam ao herói a verdade: Athena desceu viva ao Submundo, e a batalha verdadeira apenas começou. As dungeons 'Elegia da Deusa' reproduzem a perseguição aos três traidores.",
    "ranges": [(6286, 6297), (7679, 7679), (9493, 9493), (6787, 6788)], "alt": []},
   {"id": "h3", "chapter": 18, "region": "hades_castelo", "title": "Castelo de Hades: Füssen, os encantamentos de Thanatos e Hypnos e a entrada do Submundo",
    "intro": "Na Fazenda Andreas e na Vila dos Mortos, o herói descobre com a antiga cozinheira do conde Heinstein e com o jovem Julian (que aqui é o irmão de uma habitante do castelo) o que aconteceu há treze anos. Com Mu, Aioria e Miro, e depois com Seiya, Shiryu, Hyoga e Shun banhados no sangue de Athena, destrói o Núcleo do Encantamento do Deus da Morte (guardado por Valentine de Harpia) no Cemitério da Paz e o do Deus do Sono na cidade adormecida de Füssen (guardado por Queen de Alraune), enfrenta Sylphid de Basilisco, Gordon de Minotauro e Radamanthys de Wyvern e segue Pandora até a entrada do Submundo.",
    "ranges": [(6298, 6347), (13215, 13215)], "alt": []},
  ]},
 {"id": "hades2", "title": "Saga de Hades: Inferno", "intro":
  "A travessia do Submundo segue as oito prisões do Inferno de Dante que Kurumada adaptou no mangá, com muitos acréscimos do jogo: o barqueiro Caronte, os três inquisidores, Lune de Balron e o Salão de Julgamento, Faraó e o duelo musical de Orfeu, Sísifo no Inferno de Pedras, Flégias de Lycaon, o Cemitério de Fogo, o Lago de Sangue onde Lei-Hu voltou como morcego, o Inferno Desértico dos três pecados, o Inferno das Serpentes, o Cócito com os Cavaleiros de Ouro congelados, Caina, Giudecca, o Muro das Lamentações e, por fim, os Campos Elísios.",
  "sections": [
   {"id": "i1", "chapter": 19, "region": "submundo", "title": "Inferno, primeira parte: do Portal ao Cemitério de Fogo",
    "intro": "O herói desperta o Oitavo Sentido para entrar vivo no Submundo com Dohko, cruza o Aqueronte com Caronte, vence os três inquisidores, perde a identidade de Cavaleiro (Saori o expulsa), liberta Camus e Shura do esquife e da espada, atravessa o Salão de Julgamento de Lune, reencontra Seiya e Shun, Kanon, Orfeu de Lira e Eurídice, Sísifo, Shiryu e Hyoga, Flégias, e destrói os Pilares dos Mortos no Cemitério de Fogo enquanto Radamanthys renasce.",
    "ranges": [(9222, 9295)], "alt": []},
   {"id": "i2", "chapter": 20, "region": "submundo", "title": "Inferno, segunda parte: do Lago de Sangue ao Muro das Lamentações",
    "intro": "Sylphid de Basilisco captura Shiryu e Hyoga e lança a maldição de sangue; Lei-Hu, transformado em morcego, ajuda a atravessar o Lago de Sangue; Pandora revela que quer Ikki. Seguem-se o Inferno Desértico (Ganância, Gula), o Inferno das Serpentes (Lupin e Luise, Gordon novamente), Hermes e o Abismo dos Deuses, Rodório e a bênção dos Titãs, o Cócito com Mu e os Cavaleiros de Ouro congelados, Harpia, Caina, Giudecca, o sacrifício de Shaka e dos doze Cavaleiros de Ouro no Muro das Lamentações, Minos, e a morte de Pandora.",
    "ranges": [(9681, 9755)], "alt": []},
   {"id": "i3", "chapter": 21, "region": "elisios", "title": "Campos Elísios: Thanatos, Hypnos, Perséfone e Hades",
    "intro": "Além do Muro, a Floresta das Canções Mágicas, o Campo das Flores Adormecidas do Deus do Sonho, a Urna Divina onde Athena está presa, Thanatos e Hypnos, a Imperatriz do Submundo Perséfone diante do Templo de Hades e o corpo verdadeiro de Hades, na ilha flutuante acima do Coração do Rio. A vitória devolve o mundo à luz.",
    "ranges": [(15530, 15618), (12408, 12408), (12416, 12416), (12661, 12661), (15505, 15505), (15369, 15369), (15415, 15415), (12607, 12607)], "alt": []},
  ]},
]

# Histórias dos personagens (Professor Kurumada): detectadas pelo nome "A história de X (n/m)"

# Missões secundárias e eventos, agrupadas por região (faixas de ids; o que sobrar cai em "Outras")
SIDE_GROUPS = [
 ("Terra das Constelações e Santuário", "constelacoes", [(243, 300), (327, 330), (1271, 1271), (1543, 1575), (2306, 2311), (2743, 2745), (4093, 4094), (4449, 4449), (5342, 5342), (5743, 5744), (6097, 6265), (8104, 8123), (8214, 8216), (8276, 8317), (8402, 8405), (8557, 8557), (9536, 9538), (9914, 9916), (10442, 10446), (11102, 11108), (11626, 11626), (11659, 11661), (11756, 11832), (11881, 11889), (12106, 12128), (12203, 12217), (12392, 12406), (13955, 13966), (14280, 14280), (14482, 14490), (20819, 20819), (21096, 21099), (21350, 21362), (21637, 21637), (21990, 21990), (22468, 22468), (22558, 22583), (22609, 22674), (22760, 22793), (23048, 23050), (23084, 23088), (23132, 23134), (23233, 23233), (23255, 23255)]),
 ("Coliseu Graad, Cidade Prata e Vila Xintoísta", "coliseu", [(1329, 1348), (1349, 1359), (2056, 2056), (2109, 2109), (3491, 3496), (4419, 4419), (5183, 5183), (5439, 5445), (7815, 7843), (7859, 7868)]),
 ("Rozan e a Vila do Dragão Oculto", "rozan", [(696, 780), (922, 1013), (3559, 3565), (3674, 3682), (3912, 3915), (4164, 4164), (6896, 6922), (7756, 7768), (8469, 8472), (8553, 8556), (9123, 9132), (11448, 11453)]),
 ("Estrada Esquecida e Cabo Súnion", "estrada", [(2571, 2652), (3683, 3688), (3965, 3973), (4222, 4223), (4265, 4270), (8384, 8390), (8443, 8443), (11628, 11633)]),
 ("Ilha da Rainha da Morte", "ilha_rainha", [(3586, 3670), (3693, 3715), (4058, 4066), (7361, 7363), (8146, 8146), (8643, 8643), (8826, 8826), (8834, 8834)]),
 ("Sibéria Oriental e Yggdrasil", "siberia", [(4958, 5072), (5091, 5092), (5433, 5437), (5448, 5455), (5503, 5514), (5695, 5701), (6964, 6973), (7883, 7883), (8185, 8191), (8566, 8566), (14985, 14985)]),
 ("Atlântida", "atlantida", [(5229, 5262), (5334, 5341), (6974, 6983), (8587, 8616), (8759, 8857), (9857, 9857), (11711, 11711), (14846, 14846), (15369, 15369)]),
 ("Ilha de Andrômeda", "andromeda", [(6003, 6042), (6984, 6992), (9584, 9652)]),
 ("Castelo de Hades", "hades_castelo", [(6433, 6471), (6993, 7003), (8963, 8970), (9202, 9209), (9301, 9301), (9527, 9527), (12140, 12159)]),
 ("Submundo", "submundo", [(10590, 10652), (11148, 11213), (11418, 11418), (11866, 11878), (14581, 14581), (15743, 15745), (15847, 15847)]),
]

# Padrões de nome que marcam missões de sistema/teste/repetitivas: ficam fora do corpo principal (listadas só no apêndice)
SYSTEM_PATTERNS = [r"^Quest de teste", r"^Testar ", r"^Teste de (atualização|arco|QTE)", r"_Quest de teste", r"^Subquest", r"^Sub-?[Tt]arefa", r"^Subtarefas", r"^\d+ subtasks", r"^Quest [12]$", r"^Opção [12]$", r"^Continuação \d", r"^Testar Quest", r"^Exibir todas", r"^Sem o ", r"^Sem a ", r"^Liu Chunfeng", r"^1º Quest de teste", r"^Quest de teste de Benefícios", r"^Escolha a real", r"^Teste de Arco", r"^Que de Armazém", r"^Quest de Armazém", r"^Liberação do prêmio", r"^Ativa o Poço", r"^Chegar em um local", r"^1ª horda", r"^Derrotar a 1ª", r"^Caminho 1 do", r"^Doze Casas de Ouro Divinas - Versão", r"^Erradicar o Mal das Doze Casas Divinas \(zanshi\)", r"^Anular Yu Ling"]
