import random
import sys

# TODO

# Diction:
# - use indef art when they have no memory of an item that they see
# - dramatic irony would be really nice, but hard to pull off.  Well, a certain
#   amount happens naturally now, with character pov.  but more could be done
# - "Chapter 3.  _In which Bob hides the stolen jewels in the mailbox, etc_" --
#   i.e. chapter summaries -- that's a little too fancy to hope for, but with
#   a sufficiently smart Editor it could be done

### EVENTS ###

class Event(object):
    def __init__(self, phrase, participants, excl=False,
                 previous_location=None,
                 speaker=None,
                 addressed_to=None,
                 exciting=False):
        """participants[0] is always the initiator, and we
        record the location that the event was initiated in.

        For now, we assume such an event can be:
        - observed by every actor at that location
        - affects only actors at that location

        In the future, we *may* have:
        - active and passive participants
        - active participants all must be present at the location
        - passive participants need not be
        (probably done by passing a number n: the first n
        participants are to be considered active)

        speaker and addressed_to apply to dialogue.
        If speaker == None, it means the narrator is speaking.
        If addressed_to == None, it means the reader is being spoken to.

        """
        self.phrase = phrase
        self.participants = participants
        self.location = participants[0].location
        self._previous_location = previous_location
        self.excl = excl
        self.speaker = speaker
        self.addressed_to = addressed_to
        self.exciting = exciting

    def rephrase(self, new_phrase):
        """Does not modify the event.  Returns a new copy."""
        return Event(new_phrase, self.participants, excl=self.excl)

    def initiator(self):
        return self.participants[0]

    def previous_location(self):
        return self._previous_location

    def render(self):
        phrase = self.phrase
        i = 0
        for participant in self.participants:
            phrase = phrase.replace('<%d>' % (i + 1), participant.render(event=self))
            phrase = phrase.replace('<indef-%d>' % (i + 1), participant.indefinite())
            phrase = phrase.replace('<his-%d>' % (i + 1), participant.posessive())
            phrase = phrase.replace('<him-%d>' % (i + 1), participant.accusative())
            phrase = phrase.replace('<he-%d>' % (i + 1), participant.pronoun())
            phrase = phrase.replace('<was-%d>' % (i + 1), participant.was())
            phrase = phrase.replace('<is-%d>' % (i + 1), participant.is_())
            i = i + 1
        return phrase

    def __str__(self):
        phrase = self.render()
        if self.excl:
            phrase = phrase + '!'
        else:
            phrase = phrase + '.'
        return phrase[0].upper() + phrase[1:]


class AggregateEvent(Event):
    """Attempt at a way to combine multiple events into a single
    sentence.  Each constituent event must have the same initiator.

    This is definitely not as nice as it could be.

    """
    def __init__(self, template, events, excl=False):
        self.template = template
        self.events = events
        self.excl = excl
        self.phrase = 'SEE SUBEVENTS PLZ'
        self._initiator = self.events[0].initiator()
        for event in self.events:
            assert event.initiator() == self._initiator
        self.location = self._initiator.location

    def rephrase(self, new_phrase):
        #raise NotImplementedError
        return self

    def initiator(self):
        return self._initiator

    def previous_location(self):
        return self.events[0].previous_location()

    def __str__(self):
        phrase = self.template % tuple([x.render() for x in self.events])
        if self.excl:
            phrase = phrase + '!'
        else:
            phrase = phrase + '.'
        return phrase[0].upper() + phrase[1:]


class EventCollector(object):
    def __init__(self):
        self.events = []
    
    def collect(self, event):
        if self.events and str(event) == str(self.events[-1]):
            raise ValueError('Duplicate event: %s' % event)
        if event.phrase == '<1> went to <2>':
            assert event.previous_location() is not None
            assert event.previous_location() != event.location
        self.events.append(event)


# not really needed, as emit() does nothing if there is no collector
class Oblivion(EventCollector):
    def collect(self, event):
        pass


oblivion = Oblivion()


### EDITOR AND PUBLISHER ###

class Editor(object):
    """The Editor is remarkably similar to the _peephole optimizer_ in
    compiler construction.  Instead of replacing sequences of instructions
    with more efficient but semantically equivalent sequences of
    instructions, it replaces sequences of sentences with more readable
    but semantically equivalent sequences of sentences.

    The Editor is also responsible for chopping up the sequence of
    sentences into "sensible" paragraphs.  (This might be like a compiler
    code-rewriting pass that inserts NOPs to ensure instructions are on a
    word boundary, or some such.)
    
    The Editor is also responsible for picking which character to
    follow.  (I don't think there's a compiler construction analogy for
    that.)

    Note that the event stream must start with "<Character> was in <place>"
    as the first event for each character.  Otherwise the Editor don't know
    who started where.

    Well, OK, it *used* to look a lot like a peephole optimizer.  Soon, it
    will make multiple passes.  It still looks a lot like the optimization
    phase of a compiler, though.

    """
 
    def __init__(self, collector, main_characters):
        self.events = list(reversed(collector.events))
        self.main_characters = main_characters
        self.pov_index = 0
        self.transformers = []
        # maps main characters to where they currently are (omnisciently)
        self.character_location = {}
        # maps main characters to where the reader last saw them
        self.last_seen_at = {}
        # maps characters to things that happened to them while not narrated
        self.exciting_developments = {}

    def add_transformer(self, transformer):
        self.transformers.append(transformer)

    def publish(self):
        paragraph_num = 1
        while len(self.events) > 0:
            pov_actor = self.main_characters[self.pov_index]
            paragraph_events = self.generate_paragraph_events(pov_actor)
            for transformer in self.transformers:
                if paragraph_events:
                    paragraph_events = transformer.transform(
                        self, paragraph_events, paragraph_num
                    )
            self.publish_paragraph(paragraph_events)
            self.pov_index += 1
            if self.pov_index >= len(self.main_characters):
                self.pov_index = 0
            paragraph_num += 1

    def generate_paragraph_events(self, pov_actor):
        quota = random.randint(10, 25)
        paragraph_events = []
        while len(paragraph_events) < quota and len(self.events) > 0:
            event = self.events.pop()

            if not paragraph_events:
                # this is the first sentence of the paragraph
                # if the reader wasn't aware they were here, add an event
                if self.last_seen_at.get(pov_actor, None) != event.location:
                    if not (('went to' in event.phrase) or
                            ('made <his-1> way to' in event.phrase) or
                            (event.phrase == '<1> <was-1> in <2>')):
                        paragraph_events.append(Event('<1> <was-1> in <2>', [pov_actor, event.location]))
                # if something exciting happened, tell the reader
                for (obj, loc) in self.exciting_developments.get(pov_actor, []):
                    paragraph_events.append(Event('<1> had found <2> in <3>', [pov_actor, obj, loc]))
                self.exciting_developments[pov_actor] = []

            # update our idea of where the character is, even if these are
            # not events we will be dumping out
            self.character_location[event.initiator()] = event.location

            if event.location == self.character_location[pov_actor]:
                paragraph_events.append(event)
                # update the reader's idea of where the character is
                self.last_seen_at[event.initiator()] = event.location
            else:
                if event.exciting:
                   self.exciting_developments.setdefault(event.initiator(), []).append(
                       (event.participants[1], event.participants[2])
                   )

        return paragraph_events

    def publish_paragraph(self, paragraph_events):
        for event in paragraph_events:
            sys.stdout.write(str(event) + "  ")
            #sys.stdout.write("\n")
        print
        print


class Transformer(object):
    pass


class DeduplicateTransformer(Transformer):
    # check for verbatim repeated. this could be 'dangerous' if, say,
    # you have two characters, Bob Jones and Bob Smith, and both are
    # named 'Bob', and they are actually two different events... but...
    # for now that is an edge case.
    def transform(self, editor, incoming_events, paragraph_num):
        events = []
        for event in incoming_events:
            if events:
                if str(event) == str(events[-1]):
                    events[-1].phrase = event.phrase + ', twice'
                elif str(event.rephrase(event.phrase + ', twice')) == str(events[-1]):
                    events[-1].phrase = event.phrase + ', several times'
                elif str(event.rephrase(event.phrase + ', several times')) == str(events[-1]):
                    pass
                else:
                    events.append(event)
            else:
                events.append(event)
        return events


class UsePronounsTransformer(Transformer):
    # replace repeated proper nouns with pronouns
    def transform(self, editor, incoming_events, paragraph_num):
        events = []
        for event in incoming_events:
            if events:
                if event.initiator() == events[-1].initiator():
                    event.phrase = event.phrase.replace('<1>', '<he-1>')
                events.append(event)
            else:
                events.append(event)
        return events


class MadeTheirWayToTransformer(Transformer):
    def transform(self, editor, incoming_events, paragraph_num):
        events = []
        for event in incoming_events:
            if (events and
                event.initiator() == events[-1].initiator()):
                if (events[-1].phrase in ('<1> went to <2>',) and
                     event.phrase == '<1> went to <2>'):
                     assert event.location == event.participants[1]
                     assert events[-1].previous_location() is not None
                     assert events[-1].location == events[-1].participants[1]
                     events[-1].phrase = '<1> made <his-1> way to <2>'
                     events[-1].participants[1] = event.participants[1]
                     events[-1].location = event.participants[1]
                elif (events[-1].phrase in ('<1> made <his-1> way to <2>',) and
                     event.phrase == '<1> went to <2>'):
                     assert event.location == event.participants[1]
                     assert events[-1].previous_location() is not None
                     assert events[-1].location == events[-1].participants[1]
                     events[-1].phrase = '<1> made <his-1> way to <2>'
                     events[-1].participants[1] = event.participants[1]
                     events[-1].location = event.participants[1]
                else:
                    events.append(event)
            else:
                events.append(event)
        return events


# well well well
from swallows.engine.objects import Actor
weather = Actor('the weather')


class AddWeatherFrifferyTransformer(Transformer):
    def transform(self, editor, incoming_events, paragraph_num):
        events = []
        if paragraph_num == 1:
            choice = random.randint(0, 3)
            if choice == 0:
                events.append(Event("It was raining", [weather]))
            if choice == 1:
                events.append(Event("It was snowing", [weather]))
            if choice == 2:
                events.append(Event("The sun was shining", [weather]))
            if choice == 3:
                events.append(Event("The day was overcast and humid", [weather]))
        return events + incoming_events


class AddParagraphStartFrifferyTransformer(Transformer):
    def transform(self, editor, incoming_events, paragraph_num):
        first_event = incoming_events[0]
        if paragraph_num == 1:
            return incoming_events
        if str(first_event).startswith("'"):
            return incoming_events
        if " had found " in str(first_event):
            return incoming_events
        if " was in " in str(first_event):
            return incoming_events
        choice = random.randint(0, 8)
        if choice == 0:
            first_event = first_event.rephrase(
                "Later on, " + first_event.phrase
            )
        if choice == 1:
            first_event = first_event.rephrase(
                "Suddenly, " + first_event.phrase
            )
        if choice == 2:
            first_event = first_event.rephrase(
                "After a moment's consideration, " + first_event.phrase
            )
        if choice == 3:
            first_event = first_event.rephrase(
                "Feeling anxious, " + first_event.phrase
            )
        return [first_event] + incoming_events[1:]


class AggregateEventsTransformer(Transformer):
    # replace "Bob went to the kitchen.  Bob saw the toaster"
    # with "Bob went to the kitchen, where he saw the toaster"
    def transform(self, editor, incoming_events, paragraph_num):
        events = []
        for event in incoming_events:
            if events:
                if ( event.initiator() == events[-1].initiator() and
                     events[-1].phrase in ('<1> went to <2>',) and
                     event.phrase in ('<1> saw <2>',) ):
                    # this *might* be better if we only do it when <1>
                    # is the pov character for this paragraph.  but it
                    # does work...
                    event.phrase = event.phrase.replace('<1>', '<he-1>')
                    events[-1] = AggregateEvent(
                        "%s, where %s", [events[-1], event],
                        excl = event.excl)
                else:
                    events.append(event)
            else:
                events.append(event)
        return events


class DetectWanderingTransformer(Transformer):
    # not used yet
    # if they 'made their way' to their current location...
    def transform(self, editor, incoming_events, paragraph_num):
        events = []
        for event in incoming_events:
            if (event.phrase == '<1> made <his-1> way to <2>' and
                event.location == event.previous_location()):
                event.phrase = '<1> wandered around for a bit, then came back to <2>'
            events.append(event)
        return events


class Publisher(object):
    def __init__(self, characters=(), setting=(), friffery=False,
                 debug=False, title='Untitled', chapters=18,
                 events_per_chapter=810):
        self.characters = characters
        self.setting = setting
        self.friffery = friffery
        self.debug = debug
        self.title = title
        self.chapters = chapters
        self.events_per_chapter = events_per_chapter

    def publish_chapter(self, chapter_num):
        collector = EventCollector()
        
        for character in self.characters:
            character.collector = collector
            # don't continue a conversation from the previous chapter, please
            character.topic = None
            character.place_in(random.choice(self.setting))

        while len(collector.events) < self.events_per_chapter:
            for character in self.characters:
                character.live()
                #print len(collector.events) # , repr([str(e) for e in collector.events])

        if self.debug:
            for character in self.characters:
                print "%s'S EVENTS:" % character.name.upper()                
                for event in collector.events:
                    if event.participants[0] != character:
                        continue
                    print "%r in %s: %s" % (
                        [p.render(event=event) for p in event.participants],
                        event.location.render(),
                        event.phrase
                    )
                print
            for character in self.characters:
                print "%s'S STATE:" % character.name.upper()
                character.dump_beliefs()
                print
            print "- - - - -"
            print

        editor = Editor(collector, self.characters)
        editor.add_transformer(MadeTheirWayToTransformer())
        editor.add_transformer(DeduplicateTransformer())
        editor.add_transformer(AggregateEventsTransformer())
        editor.add_transformer(DetectWanderingTransformer())
        # this one should be last, so prior transformers don't
        # have to worry themselves about looking for pronouns
        editor.add_transformer(UsePronounsTransformer())
        # this should be a matter of configuring what transformers
        # to use, when you instantiate a Publisher
        if self.friffery:
            editor.add_transformer(AddWeatherFrifferyTransformer())
            editor.add_transformer(AddParagraphStartFrifferyTransformer())
        editor.publish()

    def publish(self):
        print self.title
        print "=" * len(self.title)
        print

        for chapter in range(1, self.chapters+1):
            print "Chapter %d." % chapter
            print "-----------"
            print

            self.publish_chapter(chapter)
