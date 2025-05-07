import download_youtube
import generate_transcribe
import create_master_noise
import combine_noise
import chunking_audio
import sampaling_data

if __name__ == "__main__":
    download_youtube.pipeline()
    generate_transcribe.pipeline()
    create_master_noise.pipeline()
    combine_noise.pipeline()
    chunking_audio.pipeline()
    sampaling_data.pipeline()
    print("Pipeline completed successfully.")