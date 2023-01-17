#!/usr/bin/env python
questions = [
    [1 , "E;I work hard to preserve the relationship with my counterpart", "B;I try to identify the underlying issues"],
    [2 , "D;I work to defuse tense situations"                           , "A;I gain concessions by being persistent"],
    [3 , "E;I focus on solving the other party's problem"                , "D;I try to avoid unnecessary conflicts"],
    [4 , "C;I search for a fair compromise"                              , "E;I work hard to preserve the relationship"],
    [5 , "C;I suggest fair compromises"                                  , "D;I avoid personal confrontations"],
    [6 , "C;I seek the midpoint between our positions."                  , "B;I search for the problems underlying our disagreements"],
    [7 , "D;I tactfully resolve many disagreements"                      , "C;I expect 'give and take' in negotiations"],
    [8 , "A;I clearly communicate my goals"                              , "B;I focus my attention on the other side's needs"],
    [9 , "D;I prefer to put off confrontations with other people"        , "A;I win my points by making strong arguments"],
    [10, "C;I am usually willing to compromise"                          , "A;I enjoy winning concessions"],
    [11, "B;I candidly address all the problems between us"              , "E;I care more about the relationship than winning the last concession"],
    [12, "D;I try to avoid unnecessary personal conflicts"               , "C;I search for fair compromises"],
    [13, "C;I give concessions and expect some concessions in return"    , "A;I strive to achieve all my goals in negotiations"],
    [14, "A;I enjoy getting concessions more than making them"           , "E;I strive to maintain the relationship"],
    [15, "E;I accommodate their needs to preserve the relationship"      , "D;I leave confrontational situations to others if I can"],
    [16, "E;I try to address to the other person's needs"                , "A;I work hard to achieve all my goals"],
    [17, "A;I make sure to discuss my goals"                             , "D;I emphasize areas on which we agree"],
    [18, "E;I am always looking out for the relationship"                , "C;I give concessions and expect the other side to do site same"],
    [19, "B;I identify and discuss all of our differences"               , "D;I try to avoid confrontations"],
    [20, "A;I obtain my share of concessions"                            , "E;I strive to maintain relationships"],
    [21, "B;I identify and discuss all of our differences"               , "C;I look for the compromises that might bridge the gap"],
    [22, "E;I develop good relations with the other party"               , "B;I develop options that address both alone needs"],
    [23, "C;I seek the middle ground"                                    , "A;I strive to achieve my goals in negotiations"],
    [24, "B;I identify all of our differences and look for solutions"    , "D;1 try to avoid unnecessary conflicts"],
    [25, "B;I try to preserve the relationship with my counterpart"      , "C;I search for fair compromises"],
    [26, "D;I emphasize the issues on which we agree"                    , "B;I uncover and address the things on which we disagree"],
    [27, "A;I work hard to achieve my goals"                             , "B;I pay attention to the other person's needs"],
    [28, "C;I look for the fair compromise"                              , "B;I try to identify all of the underlying problems"],
    [29, "D;I avoid unnecessary disagreements"                           , "E;I focus on solving the other person's problem"],
    [30, "A;I strive to achieve my goals"                                , "B;I work to address everyone's needs"],
]
totals={'A':0, 'B':0, 'C':0, 'D':0, 'E':0,}
for question in questions:
    letters  = [question[1].split(';')[0],question[2].split(';')[0]]
    texts    = [question[1].split(';')[1],question[2].split(';')[1]]
    print(f'\nSelect statement you think is more accurate for you {question[0]}/{len(questions)}:')
    option = -1
    while option != 1 and option != 0:
        try:
            print(f' 0: {texts[0]}')
            print(f' 1: {texts[1]}')
            option = int(input())
        except:
            option = -1
    totals[letters[option]] += 1

total = sum(totals.values())
def formatted_percentate(letter:str) -> str:
    s = "{:.1f}%".format(totals[letter]*100/total)
    return "{:>5}".format(s)

print('\n\n----------------------------------------------------------------')
print('Your bargaining style assessment results:\n')
print(f'A: {formatted_percentate("A")}')
print(f'B: {formatted_percentate("B")}')
print(f'C: {formatted_percentate("C")}')
print(f'D: {formatted_percentate("D")}')
print(f'E: {formatted_percentate("E")}')
print(f'\nDone.\n\n')
