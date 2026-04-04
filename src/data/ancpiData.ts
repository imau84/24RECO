export type JudetData = {
  judet: string;
  extravilan_agricol: number;
  extravilan_neagricol: number;
  intravilan_cu_constructii: number;
  intravilan_fara_constructii: number;
  unitati_individuale: number;
  total: number;
  // computed
  total_terenuri: number;
  cod: string; // ISO code for map
};

export const ancpiMartie2026: JudetData[] = [
  { judet: "ALBA", extravilan_agricol: 416, extravilan_neagricol: 16, intravilan_cu_constructii: 309, intravilan_fara_constructii: 167, unitati_individuale: 247, total: 1155, total_terenuri: 908, cod: "AB" },
  { judet: "ARAD", extravilan_agricol: 523, extravilan_neagricol: 14, intravilan_cu_constructii: 287, intravilan_fara_constructii: 184, unitati_individuale: 202, total: 1210, total_terenuri: 1008, cod: "AR" },
  { judet: "ARGEȘ", extravilan_agricol: 194, extravilan_neagricol: 23, intravilan_cu_constructii: 167, intravilan_fara_constructii: 289, unitati_individuale: 176, total: 849, total_terenuri: 673, cod: "AG" },
  { judet: "BACĂU", extravilan_agricol: 228, extravilan_neagricol: 10, intravilan_cu_constructii: 229, intravilan_fara_constructii: 226, unitati_individuale: 234, total: 927, total_terenuri: 693, cod: "BC" },
  { judet: "BIHOR", extravilan_agricol: 408, extravilan_neagricol: 27, intravilan_cu_constructii: 400, intravilan_fara_constructii: 312, unitati_individuale: 204, total: 1351, total_terenuri: 1147, cod: "BH" },
  { judet: "BISTRIȚA NĂSĂUD", extravilan_agricol: 78, extravilan_neagricol: 6, intravilan_cu_constructii: 190, intravilan_fara_constructii: 154, unitati_individuale: 105, total: 533, total_terenuri: 428, cod: "BN" },
  { judet: "BOTOȘANI", extravilan_agricol: 475, extravilan_neagricol: 18, intravilan_cu_constructii: 137, intravilan_fara_constructii: 161, unitati_individuale: 95, total: 886, total_terenuri: 791, cod: "BT" },
  { judet: "BRĂILA", extravilan_agricol: 617, extravilan_neagricol: 23, intravilan_cu_constructii: 100, intravilan_fara_constructii: 24, unitati_individuale: 85, total: 849, total_terenuri: 764, cod: "BR" },
  { judet: "BRAȘOV", extravilan_agricol: 337, extravilan_neagricol: 2, intravilan_cu_constructii: 745, intravilan_fara_constructii: 653, unitati_individuale: 705, total: 2442, total_terenuri: 1737, cod: "BV" },
  { judet: "BUCUREȘTI", extravilan_agricol: 0, extravilan_neagricol: 0, intravilan_cu_constructii: 2398, intravilan_fara_constructii: 2419, unitati_individuale: 3824, total: 8641, total_terenuri: 4817, cod: "B" },
  { judet: "BUZĂU", extravilan_agricol: 673, extravilan_neagricol: 14, intravilan_cu_constructii: 241, intravilan_fara_constructii: 131, unitati_individuale: 91, total: 1150, total_terenuri: 1059, cod: "BZ" },
  { judet: "CĂLĂRAȘI", extravilan_agricol: 185, extravilan_neagricol: 7, intravilan_cu_constructii: 85, intravilan_fara_constructii: 41, unitati_individuale: 31, total: 349, total_terenuri: 318, cod: "CL" },
  { judet: "CARAȘ SEVERIN", extravilan_agricol: 127, extravilan_neagricol: 11, intravilan_cu_constructii: 90, intravilan_fara_constructii: 50, unitati_individuale: 122, total: 400, total_terenuri: 278, cod: "CS" },
  { judet: "CLUJ", extravilan_agricol: 349, extravilan_neagricol: 14, intravilan_cu_constructii: 946, intravilan_fara_constructii: 601, unitati_individuale: 945, total: 2855, total_terenuri: 1910, cod: "CJ" },
  { judet: "CONSTANȚA", extravilan_agricol: 333, extravilan_neagricol: 11, intravilan_cu_constructii: 538, intravilan_fara_constructii: 710, unitati_individuale: 623, total: 2215, total_terenuri: 1592, cod: "CT" },
  { judet: "COVASNA", extravilan_agricol: 131, extravilan_neagricol: 8, intravilan_cu_constructii: 82, intravilan_fara_constructii: 61, unitati_individuale: 71, total: 353, total_terenuri: 282, cod: "CV" },
  { judet: "DÂMBOVIȚA", extravilan_agricol: 523, extravilan_neagricol: 8, intravilan_cu_constructii: 350, intravilan_fara_constructii: 309, unitati_individuale: 127, total: 1317, total_terenuri: 1190, cod: "DB" },
  { judet: "DOLJ", extravilan_agricol: 886, extravilan_neagricol: 25, intravilan_cu_constructii: 237, intravilan_fara_constructii: 236, unitati_individuale: 186, total: 1570, total_terenuri: 1384, cod: "DJ" },
  { judet: "GALAȚI", extravilan_agricol: 379, extravilan_neagricol: 15, intravilan_cu_constructii: 186, intravilan_fara_constructii: 140, unitati_individuale: 217, total: 937, total_terenuri: 720, cod: "GL" },
  { judet: "GIURGIU", extravilan_agricol: 199, extravilan_neagricol: 1, intravilan_cu_constructii: 125, intravilan_fara_constructii: 186, unitati_individuale: 38, total: 549, total_terenuri: 511, cod: "GR" },
  { judet: "GORJ", extravilan_agricol: 209, extravilan_neagricol: 36, intravilan_cu_constructii: 152, intravilan_fara_constructii: 184, unitati_individuale: 88, total: 669, total_terenuri: 581, cod: "GJ" },
  { judet: "HARGHITA", extravilan_agricol: 258, extravilan_neagricol: 22, intravilan_cu_constructii: 258, intravilan_fara_constructii: 122, unitati_individuale: 135, total: 795, total_terenuri: 660, cod: "HR" },
  { judet: "HUNEDOARA", extravilan_agricol: 280, extravilan_neagricol: 6, intravilan_cu_constructii: 93, intravilan_fara_constructii: 105, unitati_individuale: 207, total: 691, total_terenuri: 484, cod: "HD" },
  { judet: "IALOMIȚA", extravilan_agricol: 514, extravilan_neagricol: 4, intravilan_cu_constructii: 129, intravilan_fara_constructii: 69, unitati_individuale: 42, total: 758, total_terenuri: 716, cod: "IL" },
  { judet: "IAȘI", extravilan_agricol: 265, extravilan_neagricol: 9, intravilan_cu_constructii: 468, intravilan_fara_constructii: 793, unitati_individuale: 573, total: 2108, total_terenuri: 1535, cod: "IS" },
  { judet: "ILFOV", extravilan_agricol: 83, extravilan_neagricol: 22, intravilan_cu_constructii: 1033, intravilan_fara_constructii: 2056, unitati_individuale: 795, total: 3989, total_terenuri: 3194, cod: "IF" },
  { judet: "MARAMUREȘ", extravilan_agricol: 105, extravilan_neagricol: 16, intravilan_cu_constructii: 216, intravilan_fara_constructii: 185, unitati_individuale: 172, total: 694, total_terenuri: 522, cod: "MM" },
  { judet: "MEHEDINȚI", extravilan_agricol: 195, extravilan_neagricol: 9, intravilan_cu_constructii: 116, intravilan_fara_constructii: 73, unitati_individuale: 103, total: 496, total_terenuri: 393, cod: "MH" },
  { judet: "MUREȘ", extravilan_agricol: 181, extravilan_neagricol: 8, intravilan_cu_constructii: 346, intravilan_fara_constructii: 206, unitati_individuale: 282, total: 1023, total_terenuri: 741, cod: "MS" },
  { judet: "NEAMȚ", extravilan_agricol: 264, extravilan_neagricol: 13, intravilan_cu_constructii: 204, intravilan_fara_constructii: 299, unitati_individuale: 174, total: 954, total_terenuri: 780, cod: "NT" },
  { judet: "OLT", extravilan_agricol: 421, extravilan_neagricol: 3, intravilan_cu_constructii: 112, intravilan_fara_constructii: 80, unitati_individuale: 78, total: 694, total_terenuri: 616, cod: "OT" },
  { judet: "PRAHOVA", extravilan_agricol: 207, extravilan_neagricol: 7, intravilan_cu_constructii: 439, intravilan_fara_constructii: 318, unitati_individuale: 250, total: 1221, total_terenuri: 971, cod: "PH" },
  { judet: "SĂLAJ", extravilan_agricol: 76, extravilan_neagricol: 3, intravilan_cu_constructii: 119, intravilan_fara_constructii: 113, unitati_individuale: 96, total: 407, total_terenuri: 311, cod: "SJ" },
  { judet: "SATU MARE", extravilan_agricol: 448, extravilan_neagricol: 10, intravilan_cu_constructii: 211, intravilan_fara_constructii: 159, unitati_individuale: 129, total: 957, total_terenuri: 828, cod: "SM" },
  { judet: "SIBIU", extravilan_agricol: 187, extravilan_neagricol: 6, intravilan_cu_constructii: 194, intravilan_fara_constructii: 108, unitati_individuale: 213, total: 708, total_terenuri: 495, cod: "SB" },
  { judet: "SUCEAVA", extravilan_agricol: 370, extravilan_neagricol: 25, intravilan_cu_constructii: 313, intravilan_fara_constructii: 381, unitati_individuale: 223, total: 1312, total_terenuri: 1089, cod: "SV" },
  { judet: "TELEORMAN", extravilan_agricol: 37, extravilan_neagricol: 0, intravilan_cu_constructii: 8, intravilan_fara_constructii: 0, unitati_individuale: 10, total: 55, total_terenuri: 45, cod: "TR" },
  { judet: "TIMIȘ", extravilan_agricol: 744, extravilan_neagricol: 22, intravilan_cu_constructii: 703, intravilan_fara_constructii: 394, unitati_individuale: 764, total: 2627, total_terenuri: 1863, cod: "TM" },
  { judet: "TULCEA", extravilan_agricol: 366, extravilan_neagricol: 1, intravilan_cu_constructii: 81, intravilan_fara_constructii: 51, unitati_individuale: 45, total: 544, total_terenuri: 499, cod: "TL" },
  { judet: "VÂLCEA", extravilan_agricol: 101, extravilan_neagricol: 31, intravilan_cu_constructii: 230, intravilan_fara_constructii: 240, unitati_individuale: 197, total: 799, total_terenuri: 602, cod: "VL" },
  { judet: "VASLUI", extravilan_agricol: 197, extravilan_neagricol: 6, intravilan_cu_constructii: 139, intravilan_fara_constructii: 107, unitati_individuale: 83, total: 532, total_terenuri: 449, cod: "VS" },
  { judet: "VRANCEA", extravilan_agricol: 408, extravilan_neagricol: 15, intravilan_cu_constructii: 153, intravilan_fara_constructii: 132, unitati_individuale: 96, total: 804, total_terenuri: 708, cod: "VN" },
];

export const totalNational = {
  extravilan_agricol: 12977,
  extravilan_neagricol: 527,
  intravilan_cu_constructii: 13559,
  intravilan_fara_constructii: 13229,
  unitati_individuale: 13083,
  total: 53375,
  total_terenuri: 40292,
};

export const luna = "Martie 2026";
export const sursa = "ANCPI — Agenția Națională de Cadastru și Publicitate Imobiliară";
