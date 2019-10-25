from watson_developer_cloud import SpeechToTextV1
import json
import re
import MeCab
from kana_roma_util import romaji2katakana, romaji2hiragana, kana2romaji
import click
import os
from os.path import join, dirname
from dotenv import load_dotenv
from datetime import datetime

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


def speech2text(audio_file):
    jp = 'ja-JP_BroadbandModel'
    cont_type = "audio/flac"
    audio_file = open(audio_file, "rb")
    URL = 'https://gateway-tok.watsonplatform.net/speech-to-text/api'
    APIKEY = os.environ.get("API_KEY")
    speaker_labels = True

    stt = SpeechToTextV1(iam_apikey=APIKEY, url=URL)
    sttResult = stt.recognize(audio=audio_file, content_type="audio/flac", timestamps=True, model=jp,
                              word_confidence=True, speaker_labels=speaker_labels, max_alternatives=3)
    result = sttResult.get_result()
    os.makedirs("../logs/", exist_ok=True)
    logfile = open("../logs/" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + audio_file + ".json", 'w')
    json.dump(result, open(align, 'w'), indent=2, ensure_ascii=False)
    return result


def is_non_japanese(word):
    if re.match(r'[a-zA-Z!-~︰-＠]', word):
        return True
    return False


def is_trust(confidence):
    if confidence > 0.5:
        return True
    return False


def kanji2katakana(word):
    return MeCab.Tagger().parse(word).split(',')[-2]


def extract_vowel(word):
    word = re.sub(r'[^aiueon]', '', word)
    return re.sub(r'n{2}', 'n', word)


def bigrams(word):
    if len(word) == 1:
        return [word]
    return [word[i:i+2] for i, w in zip(range(len(word) - 1), word)]


def split_time(start, end, count):
    length = end - start
    per_word = length / count
    sequences = []
    for i in range(count-1):
        sequences.append({"start": start, "end": start + per_word * 2})
        start += per_word
    return sequences


def convert_timestamp(time_stamp, word):
    align_dict = []
    start, end = time_stamp[1], time_stamp[2]
    word_vowel = extract_vowel(kana2romaji(word))
    word_bigrams = bigrams(word_vowel)
    time = split_time(start, end, len(word_vowel))
    for t, w in zip(time, word_bigrams):
        row = {"word": w, "start": t["start"], "end": t["end"]}
        align_dict.append(row)
    return align_dict


def convert_words(alternatives):
    timestamps = alternatives[0]["timestamps"]
    word_confidence = alternatives[0]["word_confidence"]
    words, valid_timestamps = [], []
    for timestamp, confidence in zip(timestamps, word_confidence):
        word = timestamp[0]
        word_converted = kanji2katakana(word)
        if is_non_japanese(word) == False and is_trust(confidence[1]) == True and word_converted != '*':
            words.append(word_converted)
            valid_timestamps.append(timestamp)
    return words, valid_timestamps


@click.command()
@click.option('--audiofile', default='audio.flac')
@click.option('--alignfile', default='output.align')
def main(audiofile, alignfile):
    s2t = speech2text(audiofile)

    align_dict = []
    for sentence in s2t["results"]:
        alternatives = sentence["alternatives"]
        words, timestamps = convert_words(alternatives)
        for t, w in zip(timestamps, words):
            align_rows = convert_timestamp(t, w)
            if align_rows:
                align_dict.append(align_rows)

    output_file = open(alignfile, 'w')
    json.dump(align_dict, output_file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
