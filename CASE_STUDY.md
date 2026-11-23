# Case study · Making the sales close auditable

[Español](CASO_DE_ESTUDIO.md) · [Run the synthetic demo](README.md#run-the-synthetic-demo)

## The decision

Finance needs to know which sales figures it can use, why exceptions remain and how to recover after a failed run. A workbook can mix sales, cancellations and adjustments. A plausible total can hide dropped rows or duplicate processing after a retry.

## What I built

I built a batch pipeline that preserves each source row in Parquet and classifies activity in PostgreSQL using dbt. The worksheet and row number provide source identity. This preserves legitimate transactions with identical values. I used exact decimals for money and retained unknown amounts as missing.

A second implementation reads the original workbook and checks counts and amounts before publication. A single transaction switches consumers to the next snapshot. The previous version stays available if a candidate fails. The CLI supports replay and date-range backfills, and the HTML report and exports expose the results for review. [Architecture (Spanish)](docs/ARQUITECTURA.md) · [Recovery exercise (Spanish)](docs/INCIDENTE_SIMULADO.md)

## What the test showed

- Both worksheets of the historical UCI Online Retail II dataset were processed, covering **1,067,371 rows**. The final run matched the independent calculation across **1,798 groups** by date and activity type. Rebuild, replay and backfill produced the same canonical data hash. [Data provenance and license (Spanish)](DATA_SOURCES.md) · [Acceptance evidence](reports/acceptance.json)
- The close was marked **provisional** because **243,007 rows** lacked a customer ID. An injected failure in the synthetic demo preserved the previous snapshot and the pipeline recovered. The local run passed 30 pytest tests, and successful builds ran 11 dbt tests each. [Measured results and run conditions (Spanish)](docs/RESULTADOS.md) · [Open interactive report](https://jorgealarcon07.github.io/jorgealarcon07/cierre-de-ventas/index.en.html)

## What I learned

A reconciled total can coexist with gaps that matter to a particular analysis. Here, source integrity supported a provisional report while missing IDs limited customer-level analysis. The dataset describes historical UK retail activity. Its amounts represent recorded activity, and it provides no direct evidence of cash flows or accounting revenue. Recovery was tested with PostgreSQL and dbt. GitHub Actions also checks that the five-stage Airflow DAG imports and that its task dependencies are wired as intended. [GitHub Actions](https://github.com/jorgealarcon07/faro-data-foundation/actions)
