import hashlib


def get_hash(file_path, save=False):
    hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)

    hex_digest = hash.hexdigest()

    if save:
        with open(f"{file_path}.sha256", "w") as f:
            f.write(hex_digest)

    return hex_digest

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="计算文件的SHA256哈希值")
    parser.add_argument("file", help="要计算哈希值的文件路径")
    parser.add_argument("--save", action="store_true", help="将哈希值保存到一个新的文件中，文件名为原文件名加上.sha256后缀")

    args = parser.parse_args()
    hash_value = get_hash(args.file, args.save)
    print(f"文件 {args.file} 的SHA256哈希值为: {hash_value}")