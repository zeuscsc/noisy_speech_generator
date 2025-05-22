TC-1 Multilingual Support 

Input: 

 
Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), 100 samples each, with length ranging from 8s to 60s. where numbers are explicitly mentioned in 30% of the samples. 
Ground truth transcriptions for each clip. 
Output: 
 
WER (Word Error Rate), WRR (Word Recognition Rate) for each language. 
 
 
TC-2 Robustness Across Accents 
Input: 

 
Voice datasets for each language (Cantonese-HK with Mandarin accent, Mandarin with Cantonese accent, English with Southeast Asian accent, English with Indian accent), 100 samples each, with length ranging from 8s to 60s. where numbers are explicitly mentioned in 30% of the samples.  
Ground truth transcriptions for each clip. 
Output: 
WER (Word Error Rate), WRR (Word Recognition Rate) and for each language. 

  

TC-3 Domain Vocabulary Support 

Input: 

 
Voice datasets for each language (English, Cantonese-HK), 50 samples each, with length ranging from 8s to 60s, where HSBC specific terms are mentioned. 
Ground truth transcriptions for each clip. 
Output: 
WER (Word Error Rate), and full vocab recognition for each language 

  

TC-4 Auto Punctuation Feature 

Input: 

 
Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), 100 samples each, with length ranging from 8s to 60s, and clear punctuation syntax (periods, commas, question marks) 
Ground truth transcriptions for each clip. 
Output: 
Proportion of correct punctuation placements for each language. 

  

TC-5 Profanity Filtering 

Input: 

 
Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), 100 samples each, with length ranging from 8s to 60s, containing profanity vocabulary 
Ground truth transcriptions for each clip. 
Output: 
Rate of profanity vocabulary identified for each language 

  

TC-6 Transcription Speed and Latency 

Input: 

 
Audio clips of lengths: 8 seconds, 30 seconds, 60 seconds. 100 samples each 
Output: 
Actual latency in seconds vs system-reported latency 

  

TC-7 Noise Robustness 

Input: 

 
Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), 50 samples each, with length ranging from 8s to 60s, mixed with various environment noise at different SNR levels. 
Output: 
WER (Word Error Rate), WRR (Word Recognition Rate) 

  

TC-8 Scalability and Resilience 

Input: 

Simulate 30k concurrent STT requests using load testers. 
Simulate a variety of poor network condition. 

Output: 

 
Error Rate (requests failed / total requests). 
Response time vs concurrent load. 
Wait time  