def count_added(old_ids, new_ids):
    return len(new_ids - old_ids)


if __name__ == "__main__":
    before = {"A", "B", "C", "D", "E", "F"}
    after = {"A", "B", "C", "D", "G", "H", "I"}
    print(count_added(before, after))
