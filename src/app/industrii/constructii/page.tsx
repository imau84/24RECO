  useEffect(() => {
    const LUNI = ["ianuarie","februarie","martie","aprilie","mai","iunie","iulie","august","septembrie","octombrie","noiembrie","decembrie"];
    const ordine = (p: string) => {
      const m = p.match(/(\S+)\s+(\d{4})$/);
      return m ? Number(m[2]) * 100 + LUNI.indexOf(m[1].toLowerCase()) : 0;
    };

    fetch("/constructii_data.json")
      .then((r) => r.json())
      .then((rows: { categorie: string; judet: string; perioada: string; valoare: number | null }[]) => {
        const date: Record<string, DataPoint[]> = {};
        rows
          .filter((r) => r.judet === "TOTAL")
          .forEach((r) => {
            (date[r.categorie] ??= []).push({ luna: r.perioada, valoare: r.valoare });
          });
        Object.values(date).forEach((serie) => serie.sort((a, b) => ordine(a.luna) - ordine(b.luna)));

        const perioade = Array.from(new Set(rows.map((r) => r.perioada))).sort((a, b) => ordine(a) - ordine(b));

        const d: ConstructiiData = {
          ultima_actualizare: perioade[perioade.length - 1] ?? "",
          unitate: "mp",
          sursa: "INS — Institutul Național de Statistică",
          matrice: "LOC108A",
          categorii: Object.keys(date),
          perioade,
          date,
        };

        setConstructiiData(d);
        const total = d.categorii.find((c) => c.toUpperCase().includes("TOTAL")) ?? d.categorii[0] ?? "";
        setCategorieActiva(total);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);
