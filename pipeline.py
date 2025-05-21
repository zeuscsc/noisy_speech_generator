import download_youtube
import generate_transcribe
import create_master_noise
import combine_noise
import chunking_audio
import testset_generator
import google_batch_stt

if __name__ == "__main__":
    download_youtube.pipeline()
    generate_transcribe.pipeline()
    create_master_noise.pipeline()
    combine_noise.pipeline()
    chunking_audio.pipeline()
    testset_generator.pipeline()
    google_batch_stt.pipeline()
    print("Pipeline completed successfully.")