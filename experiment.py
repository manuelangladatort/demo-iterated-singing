# Iterated singing demo (Anglada-Tort et al., 2023)
from statistics import mean
from markupsafe import Markup

# psynet
from psynet.js_synth import JSSynth, Note, HarmonicTimbre, InstrumentTimbre
import psynet.experiment
from psynet.asset import DebugStorage, S3Storage, LocalStorage
from psynet.consent import NoConsent
from psynet.modular_page import AudioPrompt, AudioRecordControl, ModularPage
from psynet.page import InfoPage, SuccessfulEndPage
from psynet.timeline import Event, ProgressDisplay, ProgressStage, Timeline, CodeBlock
from psynet.trial.audio import (
    AudioImitationChainTrial,
    AudioImitationChainTrialMaker,
)
from psynet.trial.imitation_chain import ImitationChainNode
from psynet.utils import get_logger
logger = get_logger()

# sing4me
from sing4me import singing_extract as sing
from . sing import melodies
from . sing.params import singing_2intervals

########################################################################################################################
# Global parameters
########################################################################################################################
DESIGN = "within"  # within vs across
SYLLABLE = 'TA'
NUM_NOTES = 3
NUM_INT = (NUM_NOTES - 1)

# trials
TIME_AFTER_SINGING = 1  # increase if NUM_INT > 2
TIME_ESTIMATE_TRIAL = 14  # increase if NUM_INT > 2
MAX_ABS_INT_ERROR_ALLOWED = 5.5  # set to 999 if NUM_INT > 2
MAX_INT_SIZE = 999
MAX_MELODY_PITCH_RANGE = 999  # deactivated
MAX_INTERVAL2REFERENCE = 10  # set to 7.5 if NUM_INT > 2
NUM_CHAINS_EXPERIMENT = 200  # decrease if NUM_INT > 2
NUM_TRIALS_PARTICIPANT = 30  # decrease if NUM_INT > 2

# singing
config = singing_2intervals  # params singing extraction (from sing4me)
reference_mode = "pitch_mode"  # pitch_mode vs previous_note vs first_note
roving_width = 2.5
roving_mean = dict(
    default=55,  # it was 55.5
    low=49,  # it was 49.5 (male)
    high=61  # it was 61.5 (female)
    )


# timbre: piano or complex_mid_ISI_long
note_duration_tonejs = 0.8
note_silence_tonejs = 0
TIMBRE = dict(
    default=HarmonicTimbre(
        attack=0.01,  # Attack phase duration in seconds
        decay=0.05,  # Decay phase duration in seconds
        sustain_amp=0.8,  # Amplitude fraction to decay to relative to max amplitude --> 0.4, 0.7
        release=0.55,  # Release phase duration in seconds
        num_harmonics=10,  # Actual number of partial harmonics to use
        roll_off=14,  # Roll-off in units of dB/octave,
    )
)
pitch_duration = note_duration_tonejs + note_silence_tonejs


# experiment parameters
initial_recruitment_size = 10
num_iterations_per_chain = 10
max_num_failed_trials_allowed = 2
target_num_participants = 30
num_chains_per_participant = 3  # only active in within
num_chains_per_experiment = 100  # only active in across

repeat_same_chain = True
save_plot = True


if DESIGN == "within":
    num_trials_per_participant = num_chains_per_participant * num_iterations_per_chain
    DESIGN_PARAMS = {
        "num_trials_per_participant": int(num_trials_per_participant),
        "num_trials_practice_test": 3,
        "num_trials_practice_feedback": 2,
        "num_iterations_per_chain": num_iterations_per_chain,
        "trials_per_node": 1,
        "balance_across_chains": True,
        "performance_threshold_block1": 0.65,
        "chain_type": "within",
        "num_chains_per_participant": num_chains_per_participant,
        "recruit_mode": "num_participants",
        "target_num_participants": target_num_participants,
        "num_chains_per_experiment": None,
        "repeat_same_chain": repeat_same_chain
    }
else:
    num_trials_per_participant = num_chains_per_experiment * num_iterations_per_chain
    DESIGN_PARAMS = {
        "num_trials_per_participant": int(num_trials_per_participant),
        "num_trials_practice_test": 3,
        "num_trials_practice_feedback": 3,
        "num_iterations_per_chain": num_iterations_per_chain,
        "trials_per_node": 1,
        "balance_across_chains": False,
        "performance_threshold_block1": 0.65,
        "chain_type": "across",
        "num_chains_per_participant": None,
        "recruit_mode": "num_trials",
        "target_num_participants": None,
        "num_chains_per_experiment": num_chains_per_experiment,
        "repeat_same_chain": repeat_same_chain
    }


# utils
def estimate_time_per_trial(
    # estimate time for trials: melody and singing duration
        pitch_duration,
        num_pitches,
        time_after_singing
):
    melody_duration = pitch_duration * num_pitches
    singing_duration = melody_duration + time_after_singing
    return melody_duration, singing_duration


########################################################################################################################
# Experiment blocks
########################################################################################################################
def create_singing_trial(show_current_trial, target_pitches, time_estimate, melody_duration, singing_duration):
    singing_page = ModularPage(
        "singing",
        JSSynth(
            Markup(
                f"""
                <h3>Sing back the melody</h3>
                <hr>
                <b><b>This melody has {len(target_pitches)} notes</b></b>: Sing each note clearly using the syllable '{SYLLABLE}'.
                <br><i>Leave silent gaps between notes.</i>
                <br><br>
                {show_current_trial}
                <hr>
                """
            ),
            [Note(pitch) for pitch in target_pitches],
            timbre=TIMBRE,
            default_duration=note_duration_tonejs,
            default_silence=note_silence_tonejs,
        ),
        control=AudioRecordControl(
            duration=singing_duration,
            show_meter=True,
            controls=False,
            auto_advance=False,
            bot_response_media="example_audio.wav",
        ),
        events={
            "promptStart": Event(is_triggered_by="trialStart"),
            "recordStart": Event(is_triggered_by="promptEnd", delay=0.25),
        },
        progress_display=ProgressDisplay(
            stages=[
                ProgressStage(melody_duration, "Listen to the melody...", "orange"),
                ProgressStage(singing_duration, "Recording...SING THE MELODY!", "red"),
                ProgressStage(0.5, "Done!", "green", persistent=True),
            ],
        ),
        time_estimate=time_estimate,
    )
    return singing_page


class CustomTrialAnalysis(AudioImitationChainTrial):

    def analyze_recording(self, audio_file: str, output_plot: str):
        # convert to right register
        if self.participant.var.register == "high":
            target_pitches = self.definition["target_pitches"]
            reference_pitch = self.definition["reference_pitch"]
        else:
            target_pitches = [(i - 12) for i in self.definition["target_pitches"]]
            reference_pitch = self.definition["reference_pitch"] - 12

        raw = sing.analyze(
            audio_file,
            config,
            target_pitches=target_pitches,
            plot_options=sing.PlotOptions(
                save=save_plot, path=output_plot, format="png"
            ),
        )
        raw = [
            {key: melodies.as_native_type(value) for key, value in x.items()} for x in raw
        ]
        sung_pitches = [x["median_f0"] for x in raw]
        sung_intervals = melodies.convert_absolute_pitches_to_interval_sequence(
            sung_pitches,
            "previous_note"
        )
        target_intervals = melodies.convert_absolute_pitches_to_interval_sequence(
            target_pitches,
            "previous_note"
        )
        sung_intervals2reference = melodies.convert_absolute_pitches_to_intervals2reference(
            sung_pitches,
            reference_pitch
        )
        stats = sing.compute_stats(
            sung_pitches,
            target_pitches,
            sung_intervals,
            target_intervals
        )
        is_failed = melodies.failing_criteria(
            sung_intervals,
            sung_pitches,
            reference_pitch,
            NUM_INT,
            MAX_INT_SIZE,  # only used in interval representation, currently deactivated
            MAX_MELODY_PITCH_RANGE,  # only used in interval representation, currently deactivated
            reference_mode,
            stats,
            MAX_ABS_INT_ERROR_ALLOWED,  # deactivated
            (MAX_INTERVAL2REFERENCE * 2)  # only used in pitch mode
        )

        failed = is_failed["failed"]
        reason = is_failed["reason"]

        # convert back to high register
        if self.participant.var.register == "low":
            target_pitches = [(i + 12) for i in target_pitches]
            sung_pitches = [(i + 12) for i in sung_pitches]
            reference_pitch = reference_pitch + 12

        return {
            "failed": failed,
            "reason": reason,
            "register": self.participant.var.register,
            "reference_pitch": reference_pitch,
            "target_pitches": target_pitches,
            "num_target_pitches": len(target_pitches),
            "target_intervals": target_intervals,
            "sung_pitches": sung_pitches,
            "num_sung_pitches": len(sung_pitches),
            "sung_intervals": sung_intervals,
            "sung_intervals2reference": sung_intervals2reference,
            "raw": raw,
            "save_plot": save_plot,
            "stats": stats,
        }


class CustomTrial(CustomTrialAnalysis):
    time_estimate = TIME_ESTIMATE_TRIAL

    def show_trial(self, experiment, participant):
        logger.info("********** Register of participant: {0} **********".format(participant.var.register))
        logger.info("********** Trial123 definition: {} ********** ".format(self.definition))

        # convert to right register
        if self.participant.var.register == "high":
            target_pitches = self.definition["target_pitches"]
        else:
            target_pitches = [(i - 12) for i in self.definition["target_pitches"]]

        melody_duration, singing_duration = estimate_time_per_trial(
            pitch_duration,
            len(target_pitches) + 1,
            TIME_AFTER_SINGING
        )

        current_trial = self.position + 1
        total_num_trials = DESIGN_PARAMS["num_trials_per_participant"]
        show_current_trial = f'<br><br>Trial number {current_trial} out of {total_num_trials} possible maximum trials.'

        pages = create_singing_trial(
            show_current_trial,
            target_pitches,
            self.time_estimate,
            melody_duration,
            singing_duration
        )

        return pages


class CustomNode(ImitationChainNode):
    def create_definition_from_seed(self, seed, experiment, participant):
        return seed

    def summarize_trials(self, trials: list, experiment, participant):
        sung_intervals2reference = [trial.analysis["sung_intervals2reference"] for trial in trials]
        sung_intervals = [trial.analysis["sung_intervals"] for trial in trials]
        register = [trial.analysis["register"] for trial in trials]

        # retrieve url
        # recording_url = [trial.answer["url"] for trial in trials]
        # recording_url_as_string = "".join([str(item) for item in recording_url])

        reference_pitch = melodies.sample_reference_pitch(
            roving_mean["high"],
            roving_width,
        )

        target_intervals2reference = [mean(x) for x in zip(*sung_intervals2reference)]
        target_intervals = [mean(x) for x in zip(*sung_intervals)]

        target_pitches = melodies.convert_intervals2reference_to_absolute_pitches(
            intervals2refernece=target_intervals2reference,
            reference_pitch=reference_pitch
        )

        return dict(
            reference_pitch=reference_pitch,
            register=register.pop(0),
            target_pitches=target_pitches,
            target_intervals=target_intervals,
            target_intervals2reference=target_intervals2reference,
            num_target_pitches=len(target_pitches),
            trial_type="node_trial"
            # recording_url=recording_url_as_string
        )

    def create_initial_seed(self, experiment, participant):
        max_interval2reference = MAX_INTERVAL2REFERENCE
        max_interval_size = MAX_ABS_INT_ERROR_ALLOWED
        num_notes = NUM_NOTES

        reference_pitch = melodies.sample_reference_pitch(
            roving_mean["high"],
            roving_width,
        )

        target_pitches = melodies.sample_absolute_pitches(
            reference_pitch=reference_pitch,
            max_interval2reference=max_interval2reference,
            num_pitches=num_notes
        )
        target_intervals = melodies.convert_absolute_pitches_to_interval_sequence(target_pitches, "previous_note")
        target_intervals2reference = melodies.convert_absolute_pitches_to_intervals2reference(
            target_pitches, reference_pitch
        )

        return dict(
            register="high",  # all melodies are generated in the high register
            reference_pitch=reference_pitch,
            max_interval2reference=max_interval2reference,
            max_interval_size=max_interval_size,
            target_pitches=target_pitches,
            target_intervals=target_intervals,
            target_intervals2reference=target_intervals2reference,
            num_target_pitches=num_notes,
            trial_type="source_trial",
            reference_mode=reference_mode
        )



########################################################################################################################
# Timeline
########################################################################################################################
class Exp(psynet.experiment.Experiment):
    label = "Iterated singing demo"

    asset_storage = DebugStorage()
    # asset_storage = LocalStorage() # uncomment this to save assets locally (main experiment)

    timeline = Timeline(
        NoConsent(),
        CodeBlock(lambda participant: participant.var.set("register", "high")),  # set singing register to high for debugg
        InfoPage(
            Markup(f"""Please imitate each melody as accurately as possible"""),
            time_estimate=5,
        ),
        AudioImitationChainTrialMaker(
            id_="imitation_chain",
            trial_class=CustomTrial,
            node_class=CustomNode,
            chain_type=DESIGN_PARAMS["chain_type"],
            expected_trials_per_participant=DESIGN_PARAMS["num_trials_per_participant"],
            max_nodes_per_chain=num_iterations_per_chain,  # only relevant in within chains
            chains_per_participant=DESIGN_PARAMS["num_chains_per_participant"],  # set to None if chain_type="across"
            chains_per_experiment=DESIGN_PARAMS["num_chains_per_experiment"],  # set to None if chain_type="within"
            trials_per_node=DESIGN_PARAMS["trials_per_node"],
            balance_across_chains=DESIGN_PARAMS["balance_across_chains"],
            check_performance_at_end=True,
            check_performance_every_trial=False,
            propagate_failure=False,
            recruit_mode=DESIGN_PARAMS["recruit_mode"],
            target_n_participants=DESIGN_PARAMS["target_num_participants"],
            allow_revisiting_networks_in_across_chains=DESIGN_PARAMS["repeat_same_chain"],
        ),
        SuccessfulEndPage(),
    )
