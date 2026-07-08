PYTHON ?= python
SKILL_DIR ?= .
INSTALL_ROOT ?= $(HOME)/.agents/skills
INSTALL_PATH ?= $(INSTALL_ROOT)/antigen-screening
COVERAGE_OUTDIR ?= coverage_output

INSTALL_RSYNC_EXCLUDES = \
	--exclude=.git/ \
	--exclude=.DS_Store \
	--exclude=.pytest_cache/ \
	--exclude=__pycache__/ \
	--exclude=backup/ \
	--exclude=dist/ \
	--exclude=local_data/ \
	--exclude=real_data_output*/ \
	--exclude=live_validation_output*/ \
	--exclude=coverage_output*/ \
	--exclude=smoke_test_output*/ \
	--exclude=tests/real_data/private/ \
	--exclude=*.xlsx

PACKAGE_ZIP_EXCLUDES = \
	'./.git/*' \
	'./.DS_Store' \
	'./.pytest_cache/*' \
	'*/__pycache__/*' \
	'./backup/*' \
	'./dist/*' \
	'./local_data/*' \
	'./real_data_output*/*' \
	'./live_validation_output*/*' \
	'./coverage_output*/*' \
	'./smoke_test_output*/*' \
	'./tests/real_data/private/*' \
	'*.xlsx' \
	'*/*.xlsx' \
	'*/*/*.xlsx' \
	'*/*/*/*.xlsx'

.PHONY: validate smoke test validate-evidence live-ecd-fixture antigen-readiness-fixture hpa-fixture-smoke screening-strategy-fixture validation-ladder-fixture coverage-fixture-smoke report-priority-fixture privacy-check all-checks-offline all-checks install-user uninstall-user package git-status

validate:
	$(PYTHON) scripts/validate_skill.py --skill-dir $(SKILL_DIR)

smoke:
	$(PYTHON) scripts/run_smoke_test.py --skill-dir $(SKILL_DIR) --outdir smoke_test_output

test:
	$(PYTHON) -m unittest discover -s tests

validate-evidence:
	$(PYTHON) scripts/run_smoke_test.py --skill-dir $(SKILL_DIR) --outdir smoke_test_output
	$(PYTHON) scripts/validate_evidence_records.py \
		--input smoke_test_output/evidence_records.jsonl \
		--schema schemas/evidence_record.schema.json

live-ecd-fixture:
	$(PYTHON) scripts/run_live_ecd_validation.py \
		--gene-symbol PDCD1 \
		--accession Q15116 \
		--outdir live_validation_output/pdcd1 \
		--human-uniprot-fixture tests/fixtures/live_uniprot/Q15116.json \
		--ensembl-fixture tests/fixtures/live_ensembl/PDCD1_human_mouse.json \
		--local-ecd-identity 1.0 \
		--no-network
	$(PYTHON) scripts/validate_evidence_records.py \
		--input live_validation_output/pdcd1/live_ecd_evidence_records.jsonl \
		--schema schemas/evidence_record.schema.json

antigen-readiness-fixture:
	$(PYTHON) scripts/run_smoke_test.py --skill-dir $(SKILL_DIR) --outdir smoke_test_output
	$(PYTHON) scripts/run_antigen_readiness.py \
		--input smoke_test_output/antigen_screening_table.tsv \
		--outdir smoke_test_output/readiness

hpa-fixture-smoke:
	$(PYTHON) scripts/run_smoke_test.py --skill-dir $(SKILL_DIR) --outdir smoke_test_output
	$(PYTHON) scripts/run_hpa_normal_tissue_risk.py \
		--input smoke_test_output/antigen_screening_table.tsv \
		--outdir smoke_test_output/hpa \
		--fixtures-dir tests/fixtures/hpa \
		--offline
	$(PYTHON) scripts/validate_evidence_records.py \
		--input smoke_test_output/hpa/hpa_evidence_records.jsonl \
		--schema schemas/evidence_record.schema.json

screening-strategy-fixture:
	$(PYTHON) scripts/run_smoke_test.py --skill-dir $(SKILL_DIR) --outdir smoke_test_output
	$(PYTHON) scripts/run_antigen_readiness.py \
		--input smoke_test_output/antigen_screening_table.tsv \
		--outdir smoke_test_output/readiness
	$(PYTHON) scripts/run_screening_strategy.py \
		--input smoke_test_output/readiness/antigen_readiness_table.tsv \
		--outdir smoke_test_output/strategy

validation-ladder-fixture:
	$(PYTHON) scripts/run_smoke_test.py --skill-dir $(SKILL_DIR) --outdir smoke_test_output
	$(PYTHON) scripts/run_antigen_readiness.py \
		--input smoke_test_output/antigen_screening_table.tsv \
		--outdir smoke_test_output/readiness
	$(PYTHON) scripts/run_screening_strategy.py \
		--input smoke_test_output/readiness/antigen_readiness_table.tsv \
		--outdir smoke_test_output/strategy
	$(PYTHON) scripts/run_validation_ladder.py \
		--input smoke_test_output/strategy/screening_strategy_plan.tsv \
		--outdir smoke_test_output/validation

coverage-fixture-smoke:
	$(PYTHON) scripts/run_smoke_test.py --skill-dir $(SKILL_DIR) --outdir smoke_test_output
	$(PYTHON) scripts/run_coverage_diagnostics.py \
		--input smoke_test_output/antigen_screening_table.tsv \
		--evidence-records smoke_test_output/evidence_records.jsonl \
		--outdir $(COVERAGE_OUTDIR)/fixture
	test -s "$(COVERAGE_OUTDIR)/fixture/coverage_diagnostics.tsv"
	test -s "$(COVERAGE_OUTDIR)/fixture/id_mapping_rescue.tsv"
	test -s "$(COVERAGE_OUTDIR)/fixture/missingness_reason_summary.json"
	test -s "$(COVERAGE_OUTDIR)/fixture/adapter_readiness_matrix.tsv"
	test -s "$(COVERAGE_OUTDIR)/fixture/coverage_report.md"
	$(PYTHON) -c 'import csv,json; rows=list(csv.DictReader(open("$(COVERAGE_OUTDIR)/fixture/coverage_diagnostics.tsv",encoding="utf-8"),delimiter="\t")); by={r["gene_symbol"]:r for r in rows}; assert {"PDCD1","CD19","ALB","MKI67"} <= set(by); assert all(by[g]["missing_reason_primary"] for g in ["PDCD1","CD19","ALB","MKI67"]); assert all(by[g]["normal_tissue_status"] != "low" for g in ["PDCD1","CD19","ALB","MKI67"]); summary=json.load(open("$(COVERAGE_OUTDIR)/fixture/missingness_reason_summary.json",encoding="utf-8")); assert summary["candidate_count"] == 4'
	$(MAKE) privacy-check

report-priority-fixture:
	$(PYTHON) scripts/run_smoke_test.py --skill-dir $(SKILL_DIR) --outdir smoke_test_output
	$(PYTHON) scripts/run_hpa_normal_tissue_risk.py \
		--input smoke_test_output/antigen_screening_table.tsv \
		--outdir smoke_test_output/hpa \
		--fixtures-dir tests/fixtures/hpa \
		--offline
	$(PYTHON) scripts/run_coverage_diagnostics.py \
		--input smoke_test_output/antigen_screening_table.tsv \
		--evidence-records smoke_test_output/evidence_records.jsonl \
		--normal-tissue-risk smoke_test_output/hpa/normal_tissue_risk.tsv \
		--outdir $(COVERAGE_OUTDIR)/fixture
	$(PYTHON) scripts/export_ranked_report.py \
		--screening-table smoke_test_output/antigen_screening_table.tsv \
		--construct-plan smoke_test_output/construct_plan.tsv \
		--normal-tissue-risk smoke_test_output/hpa/normal_tissue_risk.tsv \
		--coverage-diagnostics $(COVERAGE_OUTDIR)/fixture/coverage_diagnostics.tsv \
		--identity-preference low_for_antibody_screening \
		--outdir smoke_test_output/report_priority
	test -s smoke_test_output/report_priority/report_priority_table.tsv
	test -s smoke_test_output/report_priority/report_priority_summary.json
	test -s smoke_test_output/report_priority/report_priority_report.md
	test -s smoke_test_output/report_priority/report_priority_workbook.xlsx
	$(PYTHON) -c 'import csv; rows=list(csv.DictReader(open("smoke_test_output/report_priority/report_priority_table.tsv",encoding="utf-8"),delimiter="\t")); by={r["gene_symbol"]:r for r in rows}; assert by["CD19"]["human_mouse_divergence_class"] == "high_divergence_priority"; assert by["CD19"]["original_mouse_model_transferability_gate"] == "fail"'
	$(MAKE) privacy-check

privacy-check:
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		test -z "$$(git ls-files '*.xlsx' || true)"; \
		test -z "$$(git ls-files | grep -E '(^local_data/|^real_data_output/|^coverage_output/|^smoke_test_output/|^live_validation_output/|^dist/|\.xlsx$$)' || true)"; \
	else \
		echo "privacy-check skipped: not a git repository"; \
	fi

all-checks-offline: validate smoke test package privacy-check validate-evidence live-ecd-fixture antigen-readiness-fixture hpa-fixture-smoke screening-strategy-fixture validation-ladder-fixture coverage-fixture-smoke report-priority-fixture

all-checks: all-checks-offline
	@if [ -d "$(INSTALL_PATH)" ]; then \
		$(PYTHON) "$(INSTALL_PATH)/scripts/validate_skill.py" --skill-dir "$(INSTALL_PATH)"; \
	else \
		echo "Installed skill not found at $(INSTALL_PATH); skipping installed-copy validation"; \
	fi

install-user:
	mkdir -p "$(INSTALL_ROOT)"
	rm -rf "$(INSTALL_PATH)"
	mkdir -p "$(INSTALL_PATH)"
	rsync -a $(INSTALL_RSYNC_EXCLUDES) ./ "$(INSTALL_PATH)/"
	$(PYTHON) "$(INSTALL_PATH)/scripts/validate_skill.py" --skill-dir "$(INSTALL_PATH)"

uninstall-user:
	rm -rf "$(INSTALL_PATH)"

package:
	mkdir -p dist
	zip -qr dist/antigen-screening-skill.zip . -x $(PACKAGE_ZIP_EXCLUDES)

git-status:
	git status --short
