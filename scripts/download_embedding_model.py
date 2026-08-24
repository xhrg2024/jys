"""
下载本地 embedding 模型 bge-large-zh-v1.5（约 1.3GB）。

该目录已被 .gitignore 忽略（大体积权重不进版本库），部署时需单独下载：
    python scripts/download_embedding_model.py

优先走 ModelScope（国内快），失败回退 HuggingFace。
下载到 embeddings/bge-large-zh-v1.5，已存在则跳过。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "embeddings" / "bge-large-zh-v1.5"
MODEL_ID = "BAAI/bge-large-zh-v1.5"


def _exists():
    """已下载的判定：存在 config.json 且含权重文件（pytorch_model.bin 或 model.safetensors）。"""
    if not (DEST / "config.json").exists():
        return False
    return any((DEST / f).exists() for f in ("pytorch_model.bin", "model.safetensors"))


def main():
    if _exists():
        print(f"[跳过] 模型已存在: {DEST}")
        return

    # 1. 优先 ModelScope（国内网络）
    try:
        from modelscope import snapshot_download
        print(f"从 ModelScope 下载 {MODEL_ID} ...")
        snapshot_download(MODEL_ID, local_dir=str(DEST))
        print(f"[完成] 已下载到 {DEST}")
        return
    except Exception as e:
        print(f"[ModelScope 失败] {e}")

    # 2. 回退 HuggingFace
    try:
        from huggingface_hub import snapshot_download
        print(f"从 HuggingFace 下载 {MODEL_ID} ...")
        snapshot_download(MODEL_ID, local_dir=str(DEST))
        print(f"[完成] 已下载到 {DEST}")
    except Exception as e:
        print(f"[错误] HuggingFace 下载也失败: {e}", file=sys.stderr)
        print(
            f"请手动下载后放到 {DEST}，确保包含 config.json 与 "
            "pytorch_model.bin / model.safetensors",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
