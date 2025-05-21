import json

def extract_unique_correct_words(json_data_string):
    """
    Parses a JSON string, extracts all "correct_word" values,
    and returns a unique list of these words.

    Args:
        json_data_string: A string containing the JSON data.

    Returns:
        A list of unique "correct_word" values.
        Returns an empty list if input is invalid or no correct_words are found.
    """
    try:
        data = json.loads(json_data_string)
    except json.JSONDecodeError:
        print("錯誤：無效的 JSON 格式。")
        return []

    correct_words_set = set()

    for key in data:
        if isinstance(data[key], list):
            for item in data[key]:
                if isinstance(item, dict) and "correct_word" in item:
                    correct_word = item["correct_word"]
                    if correct_word is not None:
                        correct_words_set.add(correct_word)
        else:
            print(f"警告：鍵 '{key}' 的值不是預期的列表格式。")


    return list(correct_words_set)

if __name__ == "__main__":
    with open("key_words.all.json", "r", encoding="utf-8") as file:
        json_data_string = file.read()
    unique_words = extract_unique_correct_words(json_data_string)
    json.dump(unique_words, open("vocabulary.all.json", "w", encoding="utf-8"), ensure_ascii=False, indent=4)