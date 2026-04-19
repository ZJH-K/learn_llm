def read_lines(path):
    with open(path) as f:
        for line in f:
            yield line.rstrip("\n")

def filter_contains(lines, keyword):
    for line in lines:
        if keyword in line:
            yield line    

if __name__ == "__main__":
    pipeline = filter_contains(read_lines("access.log"), "ERROR")
    count = sum(1 for _ in pipeline)
    print(f"ERROR 行数: {count}")

