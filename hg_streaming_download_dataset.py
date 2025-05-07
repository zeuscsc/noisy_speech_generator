from datasets import load_dataset, Dataset
from itertools import islice
import os

DATASET_ID = "alvanlii/cantonese-youtube"
DATASET_CONFIG = "default"
SPLIT = "train"
# Define the range of examples you want
START_INDEX = 50
STOP_INDEX = 100 # islice stops *before* this index
NUM_EXAMPLES_TO_SAVE = STOP_INDEX - START_INDEX # Calculate how many examples this slice contains
OUTPUT_PATH = "streamed_subset" # Adjusted output path name

print(f"Attempting to stream dataset: {DATASET_ID}, split: {SPLIT}")
# Updated print statement to reflect the range
print(f"Planning to process and save examples from index {START_INDEX} up to (but not including) {STOP_INDEX}.")
print(f"This corresponds to {NUM_EXAMPLES_TO_SAVE} examples.")

streamed_examples_list = []
try:
    iterable_dataset = load_dataset(
        DATASET_ID,
        DATASET_CONFIG,
        split=SPLIT,
        streaming=True,
        trust_remote_code=True
    )
    # Use islice with start and stop indices
    print(f"Streaming initiated. Accessing examples from index {START_INDEX} to {STOP_INDEX-1}...")

    # Iterate over the specified slice of the dataset
    # islice(iterable, start, stop) yields items from index 'start' up to 'stop'-1
    sliced_iterable = islice(iterable_dataset, START_INDEX, STOP_INDEX)

    processed_count = 0
    for example in sliced_iterable:
        streamed_examples_list.append(example)
        processed_count += 1
        # Update progress based on the number of examples expected in the slice
        if processed_count % 10 == 0 or processed_count == NUM_EXAMPLES_TO_SAVE:
             print(f"   Processed {processed_count}/{NUM_EXAMPLES_TO_SAVE} examples from the slice...")

    print(f"Finished collecting {processed_count} streamed examples (from index {START_INDEX} to {START_INDEX + processed_count - 1}).")

    if not streamed_examples_list:
        print("No examples were collected from the specified range, exiting.")
        exit()

    print("Converting collected examples into a standard Dataset object...")
    small_dataset = Dataset.from_list(streamed_examples_list)
    print(f"Created Dataset object with {len(small_dataset)} examples.")

    os.makedirs(OUTPUT_PATH, exist_ok=True)
    print(f"Saving the small dataset to: {os.path.abspath(OUTPUT_PATH)}")
    small_dataset.save_to_disk(OUTPUT_PATH)
    print(f"Dataset subset successfully saved to: {os.path.abspath(OUTPUT_PATH)}")

except Exception as e:
    print(f"An error occurred during streaming or saving:")
    print(f"Error type: {type(e).__name__}")
    print(f"Error details: {e}")
    exit()

print("\nScript finished successfully.")