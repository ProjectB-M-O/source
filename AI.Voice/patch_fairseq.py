"""
Applica tutte le patch Python 3.11+ a fairseq/hydra nel venv.
Eseguito automaticamente da start.py dopo l'installazione dei pacchetti.
Compatibile con Windows e Linux (rileva automaticamente il percorso site-packages).
"""
import os
import sys
import sysconfig
import shutil


def find_site_packages() -> str:
    """Trova il percorso site-packages del Python corrente."""
    # sysconfig è il modo più affidabile e cross-platform
    site = sysconfig.get_paths()["purelib"]
    if os.path.isdir(site):
        return site
    # Fallback: cerca nella cartella del venv
    base = os.path.dirname(os.path.dirname(sys.executable))
    for candidate in [
        os.path.join(base, "Lib", "site-packages"),               # Windows
        os.path.join(base, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"),  # Linux/Mac
    ]:
        if os.path.isdir(candidate):
            return candidate
    raise RuntimeError(f"Impossibile trovare site-packages. sys.executable={sys.executable}")


SITE = find_site_packages()
print(f"Site-packages: {SITE}")


def patch(path, replacements):
    full = os.path.join(SITE, path)
    if not os.path.exists(full):
        print(f"  SKIP (file non trovato): {path}")
        return
    with open(full, encoding="utf-8") as f:
        src = f.read()
    changed = False
    for old, new in replacements:
        if old in src:
            src = src.replace(old, new)
            changed = True
        else:
            print(f"  SKIP (già patchato o non trovato): {old[:60]!r}")
    if changed:
        with open(full, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"  Patchato: {path}")
    else:
        print(f"  Nessuna modifica: {path}")


# ── 1. fairseq/dataclass/configs.py ──────────────────────────────────────────
print("1. fairseq/dataclass/configs.py")
patch("fairseq/dataclass/configs.py", [
    ("    common: CommonConfig = CommonConfig()",
     "    common: CommonConfig = field(default_factory=CommonConfig)"),
    ("    common_eval: CommonEvalConfig = CommonEvalConfig()",
     "    common_eval: CommonEvalConfig = field(default_factory=CommonEvalConfig)"),
    ("    distributed_training: DistributedTrainingConfig = DistributedTrainingConfig()",
     "    distributed_training: DistributedTrainingConfig = field(default_factory=DistributedTrainingConfig)"),
    ("    dataset: DatasetConfig = DatasetConfig()",
     "    dataset: DatasetConfig = field(default_factory=DatasetConfig)"),
    ("    optimization: OptimizationConfig = OptimizationConfig()",
     "    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)"),
    ("    checkpoint: CheckpointConfig = CheckpointConfig()",
     "    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)"),
    ("    bmuf: FairseqBMUFConfig = FairseqBMUFConfig()",
     "    bmuf: FairseqBMUFConfig = field(default_factory=FairseqBMUFConfig)"),
    ("    generation: GenerationConfig = GenerationConfig()",
     "    generation: GenerationConfig = field(default_factory=GenerationConfig)"),
    ("    eval_lm: EvalLMConfig = EvalLMConfig()",
     "    eval_lm: EvalLMConfig = field(default_factory=EvalLMConfig)"),
    ("    interactive: InteractiveConfig = InteractiveConfig()",
     "    interactive: InteractiveConfig = field(default_factory=InteractiveConfig)"),
    ("    ema: EMAConfig = EMAConfig()",
     "    ema: EMAConfig = field(default_factory=EMAConfig)"),
])

# ── 2. fairseq/__init__.py ────────────────────────────────────────────────────
print("2. fairseq/__init__.py")
patch("fairseq/__init__.py", [
    ("# initialize hydra\nfrom fairseq.dataclass.initialize import hydra_init\n\nhydra_init()",
     "# initialize hydra (wrapped for Python 3.11 compat)\ntry:\n    from fairseq.dataclass.initialize import hydra_init\n    hydra_init()\nexcept Exception:\n    pass"),
    ("import fairseq.criterions  # noqa\nimport fairseq.distributed  # noqa\nimport fairseq.models  # noqa\nimport fairseq.modules  # noqa\nimport fairseq.optim  # noqa\nimport fairseq.optim.lr_scheduler  # noqa\nimport fairseq.pdb  # noqa\nimport fairseq.scoring  # noqa\nimport fairseq.tasks  # noqa\nimport fairseq.token_generation_constraints  # noqa\n\nimport fairseq.benchmark  # noqa\nimport fairseq.model_parallel  # noqa",
     "try:\n    import fairseq.criterions  # noqa\n    import fairseq.distributed  # noqa\n    import fairseq.models  # noqa\n    import fairseq.modules  # noqa\n    import fairseq.optim  # noqa\n    import fairseq.optim.lr_scheduler  # noqa\n    import fairseq.pdb  # noqa\n    import fairseq.scoring  # noqa\n    import fairseq.tasks  # noqa\n    import fairseq.token_generation_constraints  # noqa\n    import fairseq.benchmark  # noqa\n    import fairseq.model_parallel  # noqa\nexcept Exception:\n    pass"),
])

# ── 3. hydra/conf/__init__.py ─────────────────────────────────────────────────
print("3. hydra/conf/__init__.py")
patch("hydra/conf/__init__.py", [
    ("        override_dirname: OverrideDirname = OverrideDirname()",
     "        override_dirname: OverrideDirname = field(default_factory=OverrideDirname)"),
    ("    config: JobConfig = JobConfig()",
     "    config: JobConfig = field(default_factory=JobConfig)"),
    ("    run: RunDir = RunDir()",
     "    run: RunDir = field(default_factory=RunDir)"),
    ("    sweep: SweepDir = SweepDir()",
     "    sweep: SweepDir = field(default_factory=SweepDir)"),
    ("    help: HelpConf = HelpConf()",
     "    help: HelpConf = field(default_factory=HelpConf)"),
    ("    hydra_help: HydraHelpConf = HydraHelpConf()",
     "    hydra_help: HydraHelpConf = field(default_factory=HydraHelpConf)"),
    ("    overrides: OverridesConf = OverridesConf()",
     "    overrides: OverridesConf = field(default_factory=OverridesConf)"),
    ("    job: JobConf = JobConf()",
     "    job: JobConf = field(default_factory=JobConf)"),
    ("    runtime: RuntimeConf = RuntimeConf()",
     "    runtime: RuntimeConf = field(default_factory=RuntimeConf)"),
])

# ── 4. fairseq/models/transformer/transformer_config.py ──────────────────────
print("4. fairseq/models/transformer/transformer_config.py")
patch("fairseq/models/transformer/transformer_config.py", [
    ("    encoder: EncDecBaseConfig = EncDecBaseConfig()",
     "    encoder: EncDecBaseConfig = field(default_factory=EncDecBaseConfig)"),
    ("    decoder: DecoderConfig = DecoderConfig()",
     "    decoder: DecoderConfig = field(default_factory=DecoderConfig)"),
    ("    quant_noise: QuantNoiseConfig = field(default=QuantNoiseConfig())",
     "    quant_noise: QuantNoiseConfig = field(default_factory=QuantNoiseConfig)"),
])

# ── 5. fairseq/checkpoint_utils.py — torch.load weights_only ─────────────────
print("5. fairseq/checkpoint_utils.py")
patch("fairseq/checkpoint_utils.py", [
    ("state = torch.load(f, map_location=torch.device(\"cpu\"))",
     "state = torch.load(f, map_location=torch.device(\"cpu\"), weights_only=False)"),
])

print("\nRimozione pycache...")
for pkg in ("fairseq", "hydra"):
    pkg_dir = os.path.join(SITE, pkg)
    if os.path.isdir(pkg_dir):
        for root, dirs, files in os.walk(pkg_dir):
            for d in dirs:
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)
print("Fatto.")
